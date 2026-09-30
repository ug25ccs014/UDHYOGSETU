"""Pre-submission readiness checks for an entrepreneur application.

The readiness engine combines existing project/profile data, the approval rule
catalog, attached documents, document intelligence and cross-document
validation. It is an advisory gate used to prevent incomplete submissions;
it does not make statutory determinations and never contacts government APIs.
"""

from __future__ import annotations

import re
from math import ceil
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Approval, ApprovalRule, BusinessProfile, Document, DocumentStatus, GovernmentService
from app.services.business_profile import PROFILE_REQUIRED_FIELDS
from app.services.document_intelligence import (
    CrossDocumentValidator,
    GSTIN_RE,
    PAN_RE,
    fuzzy_match,
)


_PRE_SUBMISSION_STATUSES = {"NOT_STARTED", "DRAFT"}
_BLOCKING_DOCUMENT_STATUSES = {
    DocumentStatus.REJECTED.value,
    DocumentStatus.EXPIRED.value,
    DocumentStatus.WARNING.value,
    DocumentStatus.PROCESSING.value,
    DocumentStatus.UPLOADED.value,
}

# Common requirement aliases let the readiness engine match both configured
# catalog wording and real-world filenames such as ``factory_layout.pdf``.
_DOCUMENT_ALIASES: dict[str, tuple[str, ...]] = {
    "etp calculation": ("etp", "effluent treatment plant", "effluent calculation"),
    "process flow diagram": ("process flow", "flow diagram", "process-flow", "pfd"),
    "environmental impact assessment": ("environmental impact", "impact assessment", "eia"),
    "factory plan": ("factory plan", "factory layout", "factory drawing", "factory building plan"),
    "building approval": ("building approval", "building permission", "approved building plan", "occupancy"),
    "safety certificate": ("safety certificate", "safety compliance", "safety clearance"),
    "boiler specification": ("boiler specification", "boiler spec", "boiler details"),
    "technical drawing": ("technical drawing", "technical diagram", "engineering drawing"),
    "inspection report": ("inspection report", "inspection certificate", "inspection"),
    "building layout": ("building layout", "building plan", "site layout", "floor plan"),
    "fire safety plan": ("fire safety plan", "fire plan", "fire equipment", "fire safety"),
    "noc undertaking": ("noc undertaking", "noc declaration", "no objection undertaking", "undertaking"),
    "consent to establish order": ("consent to establish", "cte order", "cte certificate"),
    "water allocation": ("water allocation", "water allotment", "water permission"),
    "etp design": ("etp design", "effluent treatment design", "treatment plant design"),
    "pan card": ("pan card", "pan certificate", "permanent account number"),
    "business address proof": ("business address", "address proof", "registered address"),
    "bank account details": ("bank account", "cancelled cheque", "bank statement"),
}


def _status_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _norm(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def _tokens(value: str | None) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", (value or "").lower())
        if token not in {"the", "and", "or", "of", "to", "for", "a", "an", "document"}
    ]


class SubmissionReadinessService:
    """Evaluate whether an owned approval is ready for entrepreneur submission."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate(self, approval_id: UUID, user_id: UUID) -> dict:
        approval = await self._get_owned_approval(approval_id, user_id)
        project = approval.project
        profile = (
            await self.db.execute(
                select(BusinessProfile).where(BusinessProfile.user_id == project.user_id)
            )
        ).scalar_one_or_none()

        rule, service = await self._resolve_requirements(approval)
        required_documents = self._required_documents(rule, service)
        attached_documents = list(approval.documents)
        project_documents = await self._project_documents(project.id)
        vault_ids = await self._vault_document_ids(profile.id if profile else None)

        profile_check = self._profile_check(profile, project, attached_documents, approval)
        document_check = self._document_check(
            required_documents, attached_documents, project_documents, vault_ids
        )
        consistency = self._consistency_check(project, profile, attached_documents)

        blockers = profile_check["blocking_issues"] + document_check["blocking_issues"] + consistency["blocking_issues"]
        warnings = profile_check["warnings"] + document_check["warnings"] + consistency["warnings"]

        profile_score = profile_check["score"]
        docs_score = document_check["completeness_score"]
        validity_score = document_check["validity_score"]
        consistency_score = consistency["score"]
        score = round(
            profile_score * 0.25
            + docs_score * 0.35
            + validity_score * 0.20
            + consistency_score * 0.20
        )

        status = _status_value(approval.status)
        submission_eligible = status in _PRE_SUBMISSION_STATUSES
        can_submit = submission_eligible and not blockers

        if not submission_eligible:
            state = "NOT_APPLICABLE"
        elif blockers:
            state = "BLOCKED"
        elif warnings:
            state = "ACTION_REQUIRED"
        else:
            state = "READY"

        return {
            "application_id": approval.application_id or str(approval.id),
            "approval_id": str(approval.id),
            "project_id": str(project.id),
            "approval_name": approval.name,
            "department": approval.department,
            "application_status": status,
            "submission_eligible": submission_eligible,
            "can_submit": can_submit,
            "readiness_state": state,
            "score": score,
            "summary": {
                "profile_score": profile_score,
                "required_documents": document_check["required_count"],
                "documents_ready": document_check["ready_count"],
                "documents_missing": document_check["missing_count"],
                "documents_blocked": document_check["blocked_count"],
                "warnings": len(warnings),
                "blockers": len(blockers),
                "cross_document_red": consistency["red_count"],
                "cross_document_yellow": consistency["yellow_count"],
            },
            "checks": [
                profile_check["check"],
                document_check["check"],
                consistency["check"],
            ],
            "document_checklist": document_check["items"],
            "issues": blockers + warnings,
            "blocking_issues": blockers,
            "warnings": warnings,
            "next_actions": self._next_actions(profile_check, document_check, consistency),
            "sources": {
                "approval_rule": str(rule.id) if rule else None,
                "service": service.slug if service else None,
                "government_api": "not_connected",
            },
        }

    async def _get_owned_approval(self, approval_id: UUID, user_id: UUID) -> Approval:
        result = await self.db.execute(
            select(Approval)
            .options(selectinload(Approval.documents), selectinload(Approval.project))
            .where(Approval.id == approval_id)
        )
        approval = result.scalar_one_or_none()
        if not approval or str(approval.project.user_id) != str(user_id):
            raise ValueError("Application not found or not owned by the current user")
        return approval

    async def _resolve_requirements(
        self, approval: Approval
    ) -> tuple[ApprovalRule | None, GovernmentService | None]:
        rule = (
            await self.db.execute(
                select(ApprovalRule).where(ApprovalRule.name == approval.name)
            )
        ).scalar_one_or_none()

        service = None
        source = approval.source or ""
        if source.startswith("explore:"):
            slug = source.split(":", 1)[1]
            service = (
                await self.db.execute(
                    select(GovernmentService).where(GovernmentService.slug == slug)
                )
            ).scalar_one_or_none()
            if service and service.approval_rule_id and not rule:
                rule = await self.db.get(ApprovalRule, service.approval_rule_id)
        return rule, service

    def _required_documents(
        self,
        rule: ApprovalRule | None,
        service: GovernmentService | None,
    ) -> list[dict]:
        entries: list[dict] = []
        seen: set[str] = set()

        def add(value: Any, source: str, default_required: bool = True) -> None:
            if isinstance(value, str):
                label = value.strip()
                required = default_required
                description = value.strip()
            elif isinstance(value, dict):
                label = (value.get("document_type") or value.get("description") or "Document").strip()
                required = bool(value.get("required", default_required))
                description = (value.get("description") or value.get("document_type") or "").strip()
            else:
                return
            key = _norm(label)
            if not key or key in seen:
                return
            seen.add(key)
            entries.append({
                "document_type": label,
                "description": description,
                "required": required,
                "source": source,
            })

        if rule:
            for value in rule.required_documents or []:
                add(value, "approval_rule")
        if service:
            for value in service.applicable_documents or []:
                add(value, "service_catalog")
        return [entry for entry in entries if entry["required"]]

    async def _project_documents(self, project_id: UUID) -> list[Document]:
        result = await self.db.execute(
            select(Document).where(Document.project_id == project_id).order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def _vault_document_ids(self, profile_id: UUID | None) -> set[str]:
        if not profile_id:
            return set()
        from app.models import business_profile_documents
        result = await self.db.execute(
            select(business_profile_documents.c.document_id).where(
                business_profile_documents.c.business_profile_id == profile_id
            )
        )
        return {str(row[0]) for row in result.all()}

    def _profile_check(
        self,
        profile: BusinessProfile | None,
        project,
        documents: list,
        approval: Approval,
    ) -> dict:
        if not profile:
            missing = list(PROFILE_REQUIRED_FIELDS.values())
            issue = {
                "code": "PROFILE_MISSING",
                "severity": "WARNING",
                "category": "profile",
                "message": "Complete your reusable Business Profile before applying to reduce repeated data entry.",
                "details": {"missing_fields": missing},
            }
            return {
                "score": 0,
                "blocking_issues": [],
                "warnings": [issue],
                "check": {"key": "profile", "label": "Business profile", "status": "WARNING", "message": issue["message"]},
            }

        missing = [
            label
            for field, label in PROFILE_REQUIRED_FIELDS.items()
            if not (getattr(profile, field, None) or "").strip()
        ]
        score = round(((len(PROFILE_REQUIRED_FIELDS) - len(missing)) / len(PROFILE_REQUIRED_FIELDS)) * 100)
        warnings = []
        blockers = []
        if missing:
            warnings.append({
                "code": "PROFILE_INCOMPLETE",
                "severity": "WARNING",
                "category": "profile",
                "message": "Business Profile is incomplete.",
                "details": {"missing_fields": missing},
            })

        if profile.company_name and project.company_name and not fuzzy_match(profile.company_name, project.company_name):
            blockers.append({
                "code": "PROFILE_PROJECT_NAME_MISMATCH",
                "severity": "BLOCKER",
                "category": "consistency",
                "message": "Business Profile company name does not match the project's company name.",
                "details": {"profile": profile.company_name, "project": project.company_name},
            })

        for field, pattern, label in (
            ("pan", PAN_RE, "PAN"),
            ("gstin", GSTIN_RE, "GSTIN"),
        ):
            value = getattr(profile, field, None)
            if value and pattern.fullmatch(value) is None:
                blockers.append({
                    "code": f"INVALID_{field.upper()}",
                    "severity": "BLOCKER",
                    "category": "profile",
                    "message": f"{label} format is invalid.",
                    "details": {"field": field},
                })

        return {
            "score": score,
            "blocking_issues": blockers,
            "warnings": warnings,
            "check": {
                "key": "profile",
                "label": "Business profile",
                "status": "BLOCKED" if blockers else ("WARNING" if warnings else "PASS"),
                "message": "Complete and consistent" if not (blockers or warnings) else "Review profile information before submission.",
                "details": {"score": score, "missing_fields": missing},
            },
        }

    def _document_check(
        self,
        requirements: list[dict],
        documents: list,
        project_documents: list,
        vault_ids: set[str],
    ) -> dict:
        items: list[dict] = []
        blocking_issues: list[dict] = []
        warnings: list[dict] = []
        ready_count = 0
        missing_count = 0
        blocked_count = 0

        used_document_ids: set[str] = set()
        for requirement in requirements:
            match = self._find_match(requirement["document_type"], documents, used_document_ids)
            if match is None:
                in_vault = self._find_vault_candidate(requirement["document_type"], project_documents, vault_ids)
                candidates = self._candidate_documents(requirement["document_type"], project_documents, {str(d.id) for d in documents})
                missing_count += 1
                detail = {
                    "requirement": requirement["document_type"],
                    "description": requirement["description"],
                    "required": True,
                    "status": "MISSING",
                    "document_id": None,
                    "file_name": None,
                    "available_in_vault": in_vault is not None,
                    "vault_document_id": str(in_vault.id) if in_vault else None,
                    "candidate_documents": candidates,
                    "action": "Attach a matching project document or upload the required document.",
                }
                items.append(detail)
                blocking_issues.append({
                    "code": "REQUIRED_DOCUMENT_MISSING",
                    "severity": "BLOCKER",
                    "category": "documents",
                    "message": f"Required document missing: {requirement['document_type']}.",
                    "details": detail,
                })
                continue

            document = match
            used_document_ids.add(str(document.id))
            status = _status_value(document.status)
            errors = list(document.validation_errors or [])
            fields = dict(document.extracted_fields or {})
            is_pending = status in {DocumentStatus.PROCESSING.value, DocumentStatus.UPLOADED.value} or not fields
            is_invalid = status in {
                DocumentStatus.REJECTED.value,
                DocumentStatus.EXPIRED.value,
                DocumentStatus.WARNING.value,
            } or bool(errors)

            if is_invalid:
                blocked_count += 1
                issue_code = "DOCUMENT_INVALID"
                if status == DocumentStatus.EXPIRED.value:
                    issue_code = "DOCUMENT_EXPIRED"
                detail = {
                    "requirement": requirement["document_type"],
                    "description": requirement["description"],
                    "required": True,
                    "status": "INVALID",
                    "document_id": str(document.id),
                    "file_name": document.file_name,
                    "document_status": status,
                    "available_in_vault": str(document.id) in vault_ids,
                    "validation_errors": errors,
                    "action": "Replace or correct this document before submission.",
                }
                items.append(detail)
                blocking_issues.append({
                    "code": issue_code,
                    "severity": "BLOCKER",
                    "category": "documents",
                    "message": f"Document needs attention: {document.file_name}.",
                    "details": detail,
                })
            elif is_pending:
                blocked_count += 1
                detail = {
                    "requirement": requirement["document_type"],
                    "description": requirement["description"],
                    "required": True,
                    "status": "VALIDATION_PENDING",
                    "document_id": str(document.id),
                    "file_name": document.file_name,
                    "document_status": status,
                    "available_in_vault": str(document.id) in vault_ids,
                    "validation_errors": errors,
                    "action": "Run document validation before submission.",
                }
                items.append(detail)
                blocking_issues.append({
                    "code": "DOCUMENT_VALIDATION_PENDING",
                    "severity": "BLOCKER",
                    "category": "documents",
                    "message": f"Document validation is incomplete: {document.file_name}.",
                    "details": detail,
                })
            else:
                ready_count += 1
                items.append({
                    "requirement": requirement["document_type"],
                    "description": requirement["description"],
                    "required": True,
                    "status": "READY",
                    "document_id": str(document.id),
                    "file_name": document.file_name,
                    "document_status": status,
                    "available_in_vault": str(document.id) in vault_ids,
                    "validation_errors": errors,
                    "action": "Ready for submission.",
                })

        required_count = len(requirements)
        completeness_score = round((ready_count / required_count) * 100) if required_count else 100
        validity_score = round((ready_count / max(required_count - missing_count, 1)) * 100) if required_count else 100
        if blocking_issues:
            warnings.append({
                "code": "DOCUMENT_CHECK_ACTION_REQUIRED",
                "severity": "WARNING",
                "category": "documents",
                "message": "Resolve all document blockers before submitting.",
                "details": {"blockers": len(blocking_issues)},
            })

        return {
            "completeness_score": completeness_score,
            "validity_score": validity_score,
            "required_count": required_count,
            "ready_count": ready_count,
            "missing_count": missing_count,
            "blocked_count": blocked_count,
            "blocking_issues": blocking_issues,
            "warnings": warnings,
            "items": items,
            "check": {
                "key": "documents",
                "label": "Required documents",
                "status": "BLOCKED" if blocking_issues else "PASS",
                "message": f"{ready_count}/{required_count} required documents ready." if required_count else "No configured documents required for this application.",
                "details": {
                    "ready": ready_count,
                    "required": required_count,
                    "missing": missing_count,
                    "blocked": blocked_count,
                },
            },
        }

    def _find_match(self, requirement: str, documents: list, used_ids: set[str]):
        scored = []
        for document in documents:
            if str(document.id) in used_ids:
                continue
            score = self._document_match_score(requirement, document)
            if score > 0:
                scored.append((score, document))
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1] if scored else None

    def _find_vault_candidate(self, requirement: str, documents: list, vault_ids: set[str]):
        for document in documents:
            if str(document.id) in vault_ids and self._document_match_score(requirement, document) > 0:
                return document
        return None

    def _candidate_documents(self, requirement: str, documents: list, attached_ids: set[str]) -> list[dict]:
        scored = []
        for document in documents:
            if str(document.id) in attached_ids:
                continue
            score = self._document_match_score(requirement, document)
            if score > 0:
                scored.append((score, document))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "document_id": str(document.id),
                "file_name": document.file_name,
                "status": _status_value(document.status),
                "document_type": (document.custom_metadata or {}).get("document_type")
                or (document.extracted_fields or {}).get("document_type"),
                "match_score": round(score, 2),
            }
            for score, document in scored[:3]
        ]

    def _document_match_score(self, requirement: str, document) -> float:
        requirement_key = _norm(requirement)
        aliases = _DOCUMENT_ALIASES.get(requirement_key, (requirement,))
        candidates = [
            (document.file_name or "", 0.9),
            ((document.custom_metadata or {}).get("document_type") or "", 1.0),
            ((document.extracted_fields or {}).get("document_type") or "", 1.0),
        ]
        for alias in aliases:
            alias_key = _norm(alias)
            for value, weight in candidates:
                value_key = _norm(value)
                if alias_key and (alias_key in value_key or value_key in alias_key):
                    return weight

        req_tokens = set(_tokens(requirement))
        if not req_tokens:
            return 0.0
        best = 0.0
        for value, _weight in candidates:
            value_tokens = set(_tokens(value))
            overlap = len(req_tokens & value_tokens)
            if overlap >= max(1, ceil(len(req_tokens) * 0.6)):
                best = max(best, overlap / len(req_tokens) * 0.75)
        return best

    def _consistency_check(self, project, profile: BusinessProfile | None, documents: list) -> dict:
        payloads = [
            {
                "id": str(document.id),
                "name": document.file_name,
                "extracted_fields": dict(document.extracted_fields or {}),
            }
            for document in documents
            if document.extracted_fields
        ]
        findings = CrossDocumentValidator().validate(payloads)
        blockers: list[dict] = []
        warnings: list[dict] = []

        for finding in findings:
            issue = {
                "code": f"CROSS_DOCUMENT_{finding['field'].upper()}",
                "severity": "BLOCKER" if finding["level"] == "RED" else "WARNING",
                "category": "consistency",
                "message": finding["message"],
                "details": finding,
            }
            (blockers if finding["level"] == "RED" else warnings).append(issue)

        # Compare high-value identity fields against the reusable profile.
        if profile:
            for field, label in (("pan", "PAN"), ("gstin", "GSTIN")):
                profile_value = getattr(profile, field, None)
                if not profile_value:
                    continue
                for document in documents:
                    extracted = (document.extracted_fields or {}).get(field)
                    if extracted and _norm(extracted) != _norm(profile_value):
                        blockers.append({
                            "code": f"PROFILE_DOCUMENT_{field.upper()}_MISMATCH",
                            "severity": "BLOCKER",
                            "category": "consistency",
                            "message": f"{label} does not match the Business Profile.",
                            "details": {
                                "profile": profile_value,
                                "document": extracted,
                                "document_id": str(document.id),
                                "file_name": document.file_name,
                            },
                        })

            if profile.company_name:
                for document in documents:
                    name = (document.extracted_fields or {}).get("name")
                    if name and not fuzzy_match(profile.company_name, name):
                        blockers.append({
                            "code": "PROFILE_DOCUMENT_NAME_MISMATCH",
                            "severity": "BLOCKER",
                            "category": "consistency",
                            "message": f"Company name in {document.file_name} does not match the Business Profile.",
                            "details": {
                                "profile": profile.company_name,
                                "document": name,
                                "document_id": str(document.id),
                            },
                        })

        red_count = sum(1 for finding in findings if finding["level"] == "RED") + sum(
            1 for issue in blockers if issue["code"].startswith("PROFILE_DOCUMENT_")
        )
        yellow_count = sum(1 for finding in findings if finding["level"] == "YELLOW")
        score = max(0, 100 - (red_count * 45) - (yellow_count * 15))

        if not payloads:
            status = "WARNING"
            message = "No extracted document fields are available for consistency validation yet."
        elif blockers:
            status = "BLOCKED"
            message = "Resolve document/profile consistency issues before submission."
        elif warnings:
            status = "WARNING"
            message = "Review the consistency warnings before submission."
        else:
            status = "PASS"
            message = "No cross-document or profile mismatches detected."

        return {
            "score": score,
            "blocking_issues": blockers,
            "warnings": warnings,
            "red_count": red_count,
            "yellow_count": yellow_count,
            "check": {
                "key": "consistency",
                "label": "Document consistency",
                "status": status,
                "message": message,
                "details": {"red": red_count, "yellow": yellow_count},
            },
        }

    @staticmethod
    def _next_actions(profile_check: dict, document_check: dict, consistency: dict) -> list[dict]:
        actions: list[dict] = []
        missing_fields = profile_check.get("check", {}).get("details", {}).get("missing_fields", [])
        if missing_fields:
            actions.append({
                "priority": "MEDIUM",
                "action": "Complete your Business Profile.",
                "details": missing_fields,
                "route": "/dashboard/profile",
            })
        missing = [item["requirement"] for item in document_check.get("items", []) if item["status"] == "MISSING"]
        if missing:
            actions.append({
                "priority": "HIGH",
                "action": "Upload or attach the missing required documents.",
                "details": missing,
                "route": "documents",
            })
        pending = [item for item in document_check.get("items", []) if item["status"] == "VALIDATION_PENDING" and item.get("document_id")]
        if pending:
            actions.append({
                "priority": "HIGH",
                "action": "Validate the pending documents before submission.",
                "details": [item["file_name"] for item in pending],
                "route": "documents",
            })
        invalid = [item for item in document_check.get("items", []) if item["status"] == "INVALID"]
        if invalid:
            actions.append({
                "priority": "HIGH",
                "action": "Replace or correct invalid documents.",
                "details": [item["file_name"] for item in invalid],
                "route": "documents",
            })
        if consistency.get("blocking_issues"):
            actions.append({
                "priority": "HIGH",
                "action": "Resolve identity or cross-document mismatches.",
                "details": [issue["message"] for issue in consistency["blocking_issues"][:5]],
                "route": "documents",
            })
        return actions[:5]
