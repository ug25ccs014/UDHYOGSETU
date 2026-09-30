"""Incentive application readiness over the existing scheme catalogue.

This layer deliberately sits *on top of* :class:`IncentiveMatcher`.  The matcher
remains the single source of truth for catalogue matching; this service adds the
application-preparation concerns the SIH problem statement calls for: criteria
explanations, reusable-document readiness, profile completeness, and a saved
operational preparation case.

All eligibility and benefit statements are advisory catalogue-derived signals,
not statutory determinations or guarantees.  No government API is called.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BusinessProfile,
    Document,
    DocumentStatus,
    IncentiveApplicationCase,
    IncentiveApplicationStatus,
    Project,
    Scheme,
    business_profile_documents,
    incentive_application_documents,
)
from app.services.business_profile import BusinessProfileService
from app.services.incentive_matcher import IncentiveMatcher


_PREPARED_STATUSES = {
    IncentiveApplicationStatus.PREPARING.value,
    IncentiveApplicationStatus.READY_FOR_SUBMISSION.value,
    IncentiveApplicationStatus.SUBMITTED_EXTERNALLY.value,
    IncentiveApplicationStatus.APPROVED.value,
    IncentiveApplicationStatus.REJECTED.value,
}
_FINAL_CASE_STATUSES = {
    IncentiveApplicationStatus.SUBMITTED_EXTERNALLY.value,
    IncentiveApplicationStatus.APPROVED.value,
    IncentiveApplicationStatus.REJECTED.value,
    IncentiveApplicationStatus.CANCELLED.value,
}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _status(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _norm(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def _tokens(value: str | None) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", (value or "").lower())
        if token not in {"the", "and", "or", "of", "to", "for", "a", "an", "scheme", "documents"}
    }


class IncentiveReadinessService:
    """Build advisory application-readiness views for catalogue scheme matches."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.matcher = IncentiveMatcher(db)

    async def project_readiness(self, project_id: UUID, user_id: UUID, limit: int = 20) -> dict:
        project = await self._owned_project(project_id, user_id)
        matches = await self.matcher.find_matching_schemes(self._project_data(project))
        matches = matches[: max(1, min(limit, 50))]
        profile = await self._profile(user_id)
        documents = await self._owned_documents(user_id)
        vault_ids = await self._vault_ids(profile.id if profile else None)
        cases = await self._cases_for_project(project_id)

        results = [
            self._analyze_match(project, profile, documents, vault_ids, match, cases.get(match["id"]))
            for match in matches
        ]
        return {
            "project_id": str(project_id),
            "project_name": project.name,
            "matches": results,
            "count": len(results),
            "note": "Advisory catalogue matching and preparation assistance only; confirm official eligibility and application requirements before submission.",
        }

    async def scheme_readiness(self, project_id: UUID, scheme_id: UUID, user_id: UUID) -> dict:
        project = await self._owned_project(project_id, user_id)
        scheme = await self._scheme(scheme_id)
        if not scheme:
            raise ValueError("Scheme not found")
        matches = await self.matcher.find_matching_schemes(self._project_data(project))
        match = next((item for item in matches if item["id"] == str(scheme.id)), None)
        if not match:
            return self._analyze_unmatched(project, scheme)

        profile = await self._profile(user_id)
        documents = await self._owned_documents(user_id)
        vault_ids = await self._vault_ids(profile.id if profile else None)
        cases = await self._cases_for_project(project_id)
        return self._analyze_match(project, profile, documents, vault_ids, match, cases.get(str(scheme.id)))

    async def prepare_case(
        self,
        project_id: UUID,
        scheme_id: UUID,
        user_id: UUID,
        document_ids: list[UUID] | None = None,
        notes: str | None = None,
    ) -> dict:
        readiness = await self.scheme_readiness(project_id, scheme_id, user_id)
        if readiness.get("readiness_state") == "NOT_MATCHED":
            raise ValueError("Scheme is not currently matched to this project profile")

        case = await self._get_case(project_id, scheme_id, user_id)
        if case is None:
            case = IncentiveApplicationCase(
                project_id=project_id,
                scheme_id=scheme_id,
                status=IncentiveApplicationStatus.PREPARING.value,
                notes=notes,
                readiness_snapshot=readiness,
                prepared_at=_now(),
            )
            self.db.add(case)
            await self.db.flush()
        elif case.status in _FINAL_CASE_STATUSES and case.status != IncentiveApplicationStatus.CANCELLED.value:
            raise ValueError("This incentive case is already submitted or decided and cannot be edited")
        else:
            case.status = IncentiveApplicationStatus.PREPARING.value
            case.notes = notes if notes is not None else case.notes
            case.readiness_snapshot = readiness
            case.prepared_at = case.prepared_at or _now()
            case.updated_at = _now()

        selected_ids = document_ids if document_ids is not None else [
            UUID(item["document_id"])
            for item in readiness.get("required_documents", [])
            if item.get("status") == "READY" and item.get("document_id")
        ]
        await self._replace_case_documents(case.id, user_id, selected_ids)
        await self._update_case_readiness(case, readiness)
        await self._audit(user_id, "incentive_application_prepared", case.id, {
            "project_id": str(project_id),
            "scheme_id": str(scheme_id),
            "document_count": len(selected_ids),
            "readiness_state": readiness.get("readiness_state"),
        })
        from app.notifications.service import NotificationService
        await NotificationService(self.db).create_once(
            user_id,
            "Incentive application prepared",
            f"Your preparation pack for {readiness.get('name') or 'the matched scheme'} is ready for review.",
            category="incentive",
            severity="success",
            project_id=project_id,
            reference_id=str(case.id),
            window_minutes=30,
        )
        await self.db.commit()
        await self.db.refresh(case)
        return await self.case_detail(case.id, user_id)

    async def case_detail(self, case_id: UUID, user_id: UUID) -> dict:
        case = await self._get_case_by_id(case_id, user_id)
        if not case:
            raise ValueError("Incentive application case not found")
        scheme = await self._scheme(case.scheme_id)
        readiness = dict(case.readiness_snapshot or {})
        selected = await self._case_document_ids(case.id)
        return {
            "case_id": str(case.id),
            "project_id": str(case.project_id),
            "scheme_id": str(case.scheme_id),
            "scheme_name": scheme.name if scheme else None,
            "status": _status(case.status),
            "notes": case.notes,
            "external_reference": case.external_reference,
            "prepared_at": case.prepared_at.isoformat() if case.prepared_at else None,
            "submitted_at": case.submitted_at.isoformat() if case.submitted_at else None,
            "approved_at": case.approved_at.isoformat() if case.approved_at else None,
            "document_ids": [str(doc_id) for doc_id in selected],
            "readiness": readiness,
            "submission_mode": "EXTERNAL_OR_MANUAL",
            "government_api_connected": False,
            "note": "Preparing or recording an external application does not transmit data to a government system in this prototype.",
        }

    async def update_case(self, case_id: UUID, user_id: UUID, **payload: Any) -> dict:
        case = await self._get_case_by_id(case_id, user_id)
        if not case:
            raise ValueError("Incentive application case not found")
        if case.status in {
            IncentiveApplicationStatus.APPROVED.value,
            IncentiveApplicationStatus.REJECTED.value,
        }:
            raise ValueError("A decided incentive case cannot be edited")

        new_status = payload.get("status")
        if new_status:
            allowed = {
                IncentiveApplicationStatus.PREPARING.value,
                IncentiveApplicationStatus.READY_FOR_SUBMISSION.value,
                IncentiveApplicationStatus.SUBMITTED_EXTERNALLY.value,
                IncentiveApplicationStatus.REJECTED.value,
                IncentiveApplicationStatus.APPROVED.value,
                IncentiveApplicationStatus.CANCELLED.value,
            }
            if new_status not in allowed:
                raise ValueError("Invalid incentive application status")

            if new_status == IncentiveApplicationStatus.READY_FOR_SUBMISSION.value:
                readiness = await self.scheme_readiness(case.project_id, case.scheme_id, user_id)
                if readiness.get("readiness_state") != "READY":
                    raise ValueError("The incentive application is not ready for submission; resolve readiness blockers first")
                await self._update_case_readiness(case, readiness)

            if new_status == IncentiveApplicationStatus.SUBMITTED_EXTERNALLY.value:
                if case.status != IncentiveApplicationStatus.READY_FOR_SUBMISSION.value:
                    raise ValueError("Only incentive applications marked Ready for Submission can be recorded as externally submitted")

            case.status = new_status
            if new_status == IncentiveApplicationStatus.SUBMITTED_EXTERNALLY.value:
                case.submitted_at = _now()
            elif new_status == IncentiveApplicationStatus.APPROVED.value:
                case.approved_at = _now()

        if "notes" in payload and payload["notes"] is not None:
            case.notes = payload["notes"]
        if "external_reference" in payload:
            case.external_reference = payload["external_reference"]

        if payload.get("document_ids") is not None:
            if case.status in _FINAL_CASE_STATUSES and case.status != IncentiveApplicationStatus.CANCELLED.value:
                raise ValueError("Documents cannot be edited after external submission/decision")
            await self._replace_case_documents(case.id, user_id, payload["document_ids"])

        case.updated_at = _now()
        await self._audit(user_id, "incentive_application_updated", case.id, {
            "status": case.status,
            "external_reference": case.external_reference,
        })
        if new_status in {
            IncentiveApplicationStatus.READY_FOR_SUBMISSION.value,
            IncentiveApplicationStatus.SUBMITTED_EXTERNALLY.value,
            IncentiveApplicationStatus.APPROVED.value,
            IncentiveApplicationStatus.REJECTED.value,
        }:
            from app.notifications.service import NotificationService
            title = {
                IncentiveApplicationStatus.READY_FOR_SUBMISSION.value: "Incentive application ready",
                IncentiveApplicationStatus.SUBMITTED_EXTERNALLY.value: "External incentive submission recorded",
                IncentiveApplicationStatus.APPROVED.value: "Incentive outcome recorded",
                IncentiveApplicationStatus.REJECTED.value: "Incentive outcome recorded",
            }[new_status]
            message = {
                IncentiveApplicationStatus.READY_FOR_SUBMISSION.value: "Your preparation pack can now be submitted through the official process.",
                IncentiveApplicationStatus.SUBMITTED_EXTERNALLY.value: "An external submission has been recorded. UDYOGSETU did not transmit the application.",
                IncentiveApplicationStatus.APPROVED.value: "An incentive approval outcome has been recorded in UDYOGSETU.",
                IncentiveApplicationStatus.REJECTED.value: "A rejection outcome has been recorded in UDYOGSETU.",
            }[new_status]
            await NotificationService(self.db).create_once(
                user_id, title, message, category="incentive",
                severity="warning" if new_status == IncentiveApplicationStatus.REJECTED.value else "success",
                project_id=case.project_id, reference_id=str(case.id), window_minutes=30,
            )
        await self.db.commit()
        return await self.case_detail(case.id, user_id)

    async def _update_case_readiness(self, case: IncentiveApplicationCase, readiness: dict) -> None:
        if case.status == IncentiveApplicationStatus.PREPARING.value and readiness.get("readiness_state") == "READY":
            case.status = IncentiveApplicationStatus.READY_FOR_SUBMISSION.value
        case.readiness_snapshot = readiness
        case.updated_at = _now()

    async def _owned_project(self, project_id: UUID, user_id: UUID) -> Project:
        result = await self.db.execute(
            select(Project).where(Project.id == project_id, Project.user_id == user_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")
        return project

    async def _profile(self, user_id: UUID) -> BusinessProfile | None:
        return (
            await self.db.execute(select(BusinessProfile).where(BusinessProfile.user_id == user_id))
        ).scalar_one_or_none()

    async def _scheme(self, scheme_id: UUID) -> Scheme | None:
        return (
            await self.db.execute(select(Scheme).where(Scheme.id == scheme_id, Scheme.is_active.is_(True)))
        ).scalar_one_or_none()

    async def _owned_documents(self, user_id: UUID) -> list[tuple[Document, Project]]:
        result = await self.db.execute(
            select(Document, Project)
            .join(Project, Project.id == Document.project_id)
            .where(Project.user_id == user_id)
            .order_by(Document.created_at.desc())
        )
        return list(result.all())

    async def _vault_ids(self, profile_id: UUID | None) -> set[str]:
        if not profile_id:
            return set()
        result = await self.db.execute(
            select(business_profile_documents.c.document_id).where(
                business_profile_documents.c.business_profile_id == profile_id
            )
        )
        return {str(row[0]) for row in result.all()}

    async def _cases_for_project(self, project_id: UUID) -> dict[str, IncentiveApplicationCase]:
        result = await self.db.execute(
            select(IncentiveApplicationCase).where(IncentiveApplicationCase.project_id == project_id)
        )
        return {str(row.scheme_id): row for row in result.scalars().all()}

    async def _get_case(self, project_id: UUID, scheme_id: UUID, user_id: UUID) -> IncentiveApplicationCase | None:
        await self._owned_project(project_id, user_id)
        result = await self.db.execute(
            select(IncentiveApplicationCase).where(
                IncentiveApplicationCase.project_id == project_id,
                IncentiveApplicationCase.scheme_id == scheme_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_case_by_id(self, case_id: UUID, user_id: UUID) -> IncentiveApplicationCase | None:
        result = await self.db.execute(
            select(IncentiveApplicationCase)
            .join(Project, Project.id == IncentiveApplicationCase.project_id)
            .where(IncentiveApplicationCase.id == case_id, Project.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def _case_document_ids(self, case_id: UUID) -> list[UUID]:
        result = await self.db.execute(
            select(incentive_application_documents.c.document_id).where(
                incentive_application_documents.c.incentive_application_case_id == case_id
            )
        )
        return [row[0] for row in result.all()]

    async def _replace_case_documents(self, case_id: UUID, user_id: UUID, document_ids: list[UUID]) -> None:
        unique_ids = list(dict.fromkeys(document_ids or []))
        if unique_ids:
            owned = (
                await self.db.execute(
                    select(Document.id)
                    .join(Project, Project.id == Document.project_id)
                    .where(Document.id.in_(unique_ids), Project.user_id == user_id)
                )
            ).scalars().all()
            owned_ids = {str(doc_id) for doc_id in owned}
            missing = [str(doc_id) for doc_id in unique_ids if str(doc_id) not in owned_ids]
            if missing:
                raise ValueError("One or more selected documents are not owned by this user")

        await self.db.execute(
            delete(incentive_application_documents).where(
                incentive_application_documents.c.incentive_application_case_id == case_id
            )
        )
        if unique_ids:
            await self.db.execute(
                insert(incentive_application_documents),
                [
                    {
                        "incentive_application_case_id": case_id,
                        "document_id": document_id,
                    }
                    for document_id in unique_ids
                ],
            )

    async def _audit(self, user_id: UUID, action: str, resource_id: UUID, details: dict) -> None:
        from app.models import AuditLog
        self.db.add(
            AuditLog(
                user_id=user_id,
                action=action,
                resource_type="incentive_application_case",
                resource_id=resource_id,
                details=details,
            )
        )

    def _analyze_match(
        self,
        project: Project,
        profile: BusinessProfile | None,
        documents: list[tuple[Document, Project]],
        vault_ids: set[str],
        match: dict,
        case: IncentiveApplicationCase | None,
    ) -> dict:
        scheme_id = match["id"]
        scheme = self._scheme_from_match(match)
        criteria = self._criteria(project, scheme)
        required_documents = self._required_documents(match, documents, vault_ids)
        profile_payload = BusinessProfileService(self.db).to_response(profile) if profile else None
        profile_score = (profile_payload or {}).get("completeness", {}).get("score", 0)
        docs_ready = sum(1 for item in required_documents if item["status"] == "READY")
        docs_required = len(required_documents)
        docs_score = round(docs_ready / docs_required * 100) if docs_required else 100
        criteria_met = sum(1 for item in criteria if item["status"] == "MET")
        criteria_hard_fail = any(item["status"] == "NOT_MET" for item in criteria)
        readiness_score = round(profile_score * 0.30 + docs_score * 0.45 + (criteria_met / max(len(criteria), 1) * 100) * 0.25)

        blockers = [
            {
                "code": "INCENTIVE_DOCUMENT_MISSING",
                "message": f"Missing required document: {item['requirement']}",
                "document": item,
            }
            for item in required_documents
            if item["status"] in {"MISSING", "INVALID"}
        ]
        if criteria_hard_fail:
            blockers.append({
                "code": "INCENTIVE_CRITERIA_NOT_MET",
                "message": "One or more configured scheme criteria are not met.",
            })

        warnings = [
            {
                "code": "INCENTIVE_PROFILE_INCOMPLETE",
                "message": "Complete the reusable Business Profile to reduce repeated information entry.",
            }
        ] if profile_score < 100 else []
        warnings.extend(
            {
                "code": "INCENTIVE_ENTITY_REVIEW",
                "message": "Eligible entity is configured in the catalogue and may require official confirmation.",
            }
            for item in criteria
            if item["key"] == "eligible_entity" and item["status"] == "REVIEW"
        )

        if criteria_hard_fail:
            readiness_state = "NOT_MATCHED"
        elif blockers:
            readiness_state = "ACTION_REQUIRED"
        elif warnings:
            readiness_state = "REVIEW_RECOMMENDED"
        else:
            readiness_state = "READY"

        return {
            "scheme_id": scheme_id,
            "name": match.get("name"),
            "department": match.get("department"),
            "sector": match.get("sector"),
            "match_score": match.get("match_score"),
            "match_reason": match.get("match_reason"),
            "benefits": match.get("benefits", []),
            "application_period": match.get("application_period"),
            "source": match.get("source"),
            "source_url": match.get("source_url"),
            "eligibility": {
                "criteria": criteria,
                "manual_confirmation_required": any(item["status"] == "REVIEW" for item in criteria),
            },
            "profile": {
                "score": profile_score,
                "complete": profile_score == 100,
            },
            "required_documents": required_documents,
            "document_summary": {
                "required": docs_required,
                "ready": docs_ready,
                "missing": sum(1 for item in required_documents if item["status"] == "MISSING"),
                "invalid": sum(1 for item in required_documents if item["status"] == "INVALID"),
            },
            "readiness_score": readiness_score,
            "readiness_state": readiness_state,
            "blockers": blockers,
            "warnings": warnings,
            "case": {
                "case_id": str(case.id) if case else None,
                "status": _status(case.status) if case else None,
                "external_reference": case.external_reference if case else None,
                "prepared_at": case.prepared_at.isoformat() if case and case.prepared_at else None,
            },
            "note": "Catalogue-derived advisory readiness; confirm the official scheme notice, current window and final document list before submission.",
        }

    def _analyze_unmatched(self, project: Project, scheme: Scheme) -> dict:
        criteria = self._criteria(project, scheme)
        return {
            "scheme_id": str(scheme.id),
            "name": scheme.name,
            "department": scheme.department,
            "sector": scheme.sector,
            "match_score": 0,
            "match_reason": "The configured matcher did not currently identify this project as a match.",
            "benefits": scheme.benefits or [],
            "application_period": scheme.application_period,
            "source": scheme.source,
            "source_url": scheme.source_url,
            "eligibility": {"criteria": criteria, "manual_confirmation_required": True},
            "profile": {"score": 0, "complete": False},
            "required_documents": [],
            "document_summary": {"required": 0, "ready": 0, "missing": 0, "invalid": 0},
            "readiness_score": 0,
            "readiness_state": "NOT_MATCHED",
            "blockers": [{"code": "SCHEME_NOT_MATCHED", "message": "Scheme is not currently matched to the project profile."}],
            "warnings": [],
            "case": {"case_id": None, "status": None, "external_reference": None, "prepared_at": None},
            "note": "Catalogue-derived advisory assessment only.",
        }

    @staticmethod
    def _scheme_from_match(match: dict) -> Scheme:
        scheme = Scheme(
            id=UUID(str(match["id"])),
            name=match.get("name") or "",
            department=match.get("department") or "",
            sector=match.get("sector"),
            location=match.get("location"),
            min_investment=match.get("min_investment"),
            max_investment=match.get("max_investment"),
            eligible_entity=match.get("eligible_entity"),
            employee_requirement=match.get("employee_requirement"),
            benefits=match.get("benefits", []),
            application_period=match.get("application_period"),
            required_documents=match.get("required_documents", []),
        )
        return scheme

    @staticmethod
    def _project_data(project: Project) -> dict:
        return {
            "industry": project.industry,
            "sector": project.sector,
            "state": project.location_state,
            "location": project.location_state,
            "investment_amount": project.investment_amount,
            "employees": project.employees,
            "business_type": project.business_type,
        }

    def _criteria(self, project: Project, scheme: Scheme) -> list[dict]:
        industry = (project.industry or project.sector or "").lower()
        scheme_sector = (scheme.sector or "").lower()
        state = (project.location_state or "").lower()
        scheme_location = (scheme.location or "").lower()
        investment = project.investment_amount
        employees = project.employees

        criteria: list[dict] = []
        if not scheme_sector or scheme_sector in {"all", "all industries"}:
            criteria.append({"key": "sector", "label": "Sector", "status": "MET", "detail": "Scheme applies across sectors according to the configured catalogue."})
        elif scheme_sector in industry or scheme_sector in (project.sector or "").lower():
            criteria.append({"key": "sector", "label": "Sector", "status": "MET", "detail": f"Project sector matches {scheme.sector}."})
        else:
            criteria.append({"key": "sector", "label": "Sector", "status": "NOT_MET", "detail": f"Project sector does not match configured scheme sector {scheme.sector}."})

        if not scheme_location or scheme_location in {"all", "all india", "india"}:
            criteria.append({"key": "location", "label": "Location", "status": "MET", "detail": "Scheme is configured without a narrower location restriction."})
        elif scheme_location == state:
            criteria.append({"key": "location", "label": "Location", "status": "MET", "detail": f"Project is located in {project.location_state}."})
        else:
            criteria.append({"key": "location", "label": "Location", "status": "NOT_MET", "detail": f"Project location {project.location_state or '—'} differs from configured location {scheme.location}."})

        if scheme.min_investment is None and scheme.max_investment is None:
            investment_status = "MET"
            detail = "No investment range is configured."
        elif investment is None:
            investment_status = "REVIEW"
            detail = "Project investment is not available."
        elif scheme.min_investment is not None and investment < scheme.min_investment:
            investment_status = "NOT_MET"
            detail = f"Investment is below the configured minimum of ₹{scheme.min_investment:,.0f}."
        elif scheme.max_investment is not None and investment > scheme.max_investment:
            investment_status = "NOT_MET"
            detail = f"Investment exceeds the configured maximum of ₹{scheme.max_investment:,.0f}."
        else:
            investment_status = "MET"
            detail = "Investment falls within the configured range."
        criteria.append({"key": "investment", "label": "Investment", "status": investment_status, "detail": detail})

        if not scheme.employee_requirement:
            employee_status = "MET"
            employee_detail = "No minimum employee count is configured."
        elif employees is None:
            employee_status = "REVIEW"
            employee_detail = "Employee count is not available."
        elif employees >= scheme.employee_requirement:
            employee_status = "MET"
            employee_detail = f"Employee count meets the configured minimum of {scheme.employee_requirement}."
        else:
            employee_status = "NOT_MET"
            employee_detail = f"Employee count is below the configured minimum of {scheme.employee_requirement}."
        criteria.append({"key": "employees", "label": "Employees", "status": employee_status, "detail": employee_detail})

        entity = (scheme.eligible_entity or "").lower().strip()
        if not entity or entity in {"all", "all entities", "all msmes"}:
            entity_status = "MET"
            entity_detail = "No narrower entity restriction is configured."
        else:
            entity_status = "REVIEW"
            entity_detail = f"Catalogue lists eligible entity as {scheme.eligible_entity}; official eligibility should be confirmed."
        criteria.append({"key": "eligible_entity", "label": "Entity type", "status": entity_status, "detail": entity_detail})
        return criteria

    def _required_documents(
        self,
        match: dict,
        documents: list[tuple[Document, Project]],
        vault_ids: set[str],
    ) -> list[dict]:
        requirements = match.get("required_documents") or []
        used: set[str] = set()
        result: list[dict] = []
        for raw in requirements:
            requirement = raw.get("document_type") if isinstance(raw, dict) else str(raw)
            requirement = (requirement or "").strip()
            if not requirement:
                continue
            candidate = self._best_document(requirement, documents, used)
            if candidate:
                document, project, score = candidate
                used.add(str(document.id))
                status = _status(document.status)
                errors = list(document.validation_errors or [])
                if status in {
                    DocumentStatus.REJECTED.value,
                    DocumentStatus.EXPIRED.value,
                    DocumentStatus.WARNING.value,
                } or errors:
                    item_status = "INVALID"
                elif status in {DocumentStatus.UPLOADED.value, DocumentStatus.PROCESSING.value} or not document.extracted_fields:
                    item_status = "VALIDATION_PENDING"
                else:
                    item_status = "READY"
                result.append({
                    "requirement": requirement,
                    "status": item_status,
                    "document_id": str(document.id),
                    "file_name": document.file_name,
                    "project_id": str(project.id),
                    "project_name": project.name,
                    "in_vault": str(document.id) in vault_ids,
                    "match_score": round(score, 2),
                    "document_status": status,
                    "validation_errors": errors,
                })
            else:
                candidates = self._document_candidates(requirement, documents, used)
                result.append({
                    "requirement": requirement,
                    "status": "MISSING",
                    "document_id": None,
                    "file_name": None,
                    "project_id": None,
                    "project_name": None,
                    "in_vault": False,
                    "candidates": candidates,
                })
        return result

    def _best_document(self, requirement: str, documents, used):
        scored = []
        for document, project in documents:
            if str(document.id) in used:
                continue
            score = self._document_score(requirement, document)
            if score > 0:
                scored.append((document, project, score))
        if not scored:
            return None
        scored.sort(key=lambda item: (item[2], item[0].created_at or datetime.min), reverse=True)
        return scored[0]

    def _document_candidates(self, requirement: str, documents, used):
        candidates = []
        for document, project in documents:
            if str(document.id) in used:
                continue
            score = self._document_score(requirement, document)
            if score > 0:
                candidates.append({
                    "document_id": str(document.id),
                    "file_name": document.file_name,
                    "project_id": str(project.id),
                    "project_name": project.name,
                    "status": _status(document.status),
                    "in_vault": False,
                    "match_score": round(score, 2),
                })
        candidates.sort(key=lambda item: item["match_score"], reverse=True)
        return candidates[:3]

    def _document_score(self, requirement: str, document: Document) -> float:
        values = [
            ((document.custom_metadata or {}).get("document_type") or "", 1.0),
            ((document.extracted_fields or {}).get("document_type") or "", 1.0),
            (document.file_name or "", 0.9),
        ]
        req_norm = _norm(requirement)
        for value, weight in values:
            val_norm = _norm(value)
            if req_norm and (req_norm in val_norm or val_norm in req_norm):
                return weight
        req_tokens = _tokens(requirement)
        if not req_tokens:
            return 0.0
        best = 0.0
        for value, _ in values:
            overlap = len(req_tokens & _tokens(value))
            if overlap:
                best = max(best, overlap / len(req_tokens) * 0.75)
        return best
