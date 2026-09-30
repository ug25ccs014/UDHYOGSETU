"""Unified project command center orchestration.

This service composes existing UDYOGSETU foundations into a single project-level
view. It deliberately does not introduce a new source of truth for approvals,
readiness, risk, inspections, grievances, compliance, or incentives.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    ApplicationPreparation,
    ApplicationQuery,
    Approval,
    ApprovalStatus,
    BusinessProfile,
    Document,
    Grievance,
    InspectionVisit,
    InspectionVisitStatus,
    Project,
    approval_documents,
    inspection_visit_approvals,
)
from app.services.approval_graph import ApprovalGraphService
from app.services.business_profile import BusinessProfileService
from app.services.compliance import ComplianceService
from app.services.incentive_readiness import IncentiveReadinessService
from app.services.sla_risk import SlaRiskService
from app.services.submission_readiness import SubmissionReadinessService


_ACTIVE_QUERY_STATUSES = {"OPEN", "DRAFT", "READY"}
_ACTIVE_GRIEVANCE_STATUSES = {"OPEN", "ACKNOWLEDGED", "IN_REVIEW", "ESCALATED"}
_ACTIVE_INSPECTION_STATUSES = {InspectionVisitStatus.SCHEDULED.value}
_PRE_SUBMISSION_STATUSES = {ApprovalStatus.NOT_STARTED.value, ApprovalStatus.DRAFT.value}
_TERMINAL_APPROVALS = {
    ApprovalStatus.APPROVED.value,
    ApprovalStatus.REJECTED.value,
    ApprovalStatus.EXPIRED.value,
    ApprovalStatus.CANCELED.value,
}


def _status(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _approval_app_id(approval: Approval) -> str:
    return approval.application_id or str(approval.id)


def _location(project: Project) -> str:
    parts = [
        project.location_city,
        project.location_district,
        project.location_state,
    ]
    return ", ".join(dict.fromkeys(p.strip() for p in parts if isinstance(p, str) and p.strip()))


class CommandCenterService:
    """Build a single, owner-scoped operational view for a project."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def build(self, project_id: UUID, user_id: UUID) -> dict:
        project = await self._get_owned_project(project_id, user_id)
        approvals = await self._get_approvals(project_id)
        profile = await self._get_profile(user_id)

        # Reuse existing services as the authoritative sources for each domain.
        graph = await ApprovalGraphService(self.db).build_graph(project_id)
        risk_portfolio = await SlaRiskService(self.db).portfolio(user_id, project_id)
        compliance = await ComplianceService(self.db).get_compliance_dashboard(project_id)
        compliance_alerts = await self._get_compliance_alerts(project_id)
        incentive_view = await IncentiveReadinessService(self.db).project_readiness(
            project_id, user_id, limit=12
        )
        incentives = incentive_view.get("matches", [])
        readiness_by_approval = await self._readiness_by_approval(approvals, project)
        preparation_by_approval = await self._preparation_by_approval(approvals)
        query_map = await self._query_signals(project_id)
        inspection_map = await self._inspection_signals(project_id)
        grievances = await self._grievances(project_id)
        documents = await self._documents(project_id)

        risk_by_approval = {
            row["approval_id"]: row for row in risk_portfolio.get("applications", [])
        }

        approval_cards = [
            self._approval_card(
                approval,
                readiness_by_approval.get(str(approval.id)),
                preparation_by_approval.get(approval.id),
                query_map.get(approval.id, 0),
                inspection_map.get(approval.id),
                risk_by_approval.get(str(approval.id)),
                compliance_alerts,
            )
            for approval in approvals
        ]

        action_center = self._build_action_center(
            project,
            profile,
            approval_cards,
            documents,
            compliance,
            compliance_alerts,
            grievances,
            incentives,
        )

        approval_status_counts = Counter(card["status"] for card in approval_cards)
        action_count = len(action_center)
        project_readiness = self._project_readiness_score(
            project,
            profile,
            approval_cards,
            compliance,
        )

        unique_inspections: dict[str, dict] = {}
        for item in inspection_map.values():
            if not item or not item.get("scheduled"):
                continue
            visit_id = item.get("visit_id") or f"scheduled-{item.get('scheduled_start')}"
            existing = unique_inspections.get(visit_id)
            if existing is None:
                unique_inspections[visit_id] = dict(item)
                continue
            for name in item.get("approval_names", []):
                if name not in existing.setdefault("approval_names", []):
                    existing["approval_names"].append(name)
        upcoming_inspections = sorted(
            unique_inspections.values(),
            key=lambda item: item.get("scheduled_start") or "",
        )

        return {
            "project": {
                "id": str(project.id),
                "name": project.name,
                "company_name": project.company_name,
                "industry": project.industry,
                "sector": project.sector,
                "project_stage": project.project_stage,
                "investment_amount": project.investment_amount,
                "location": _location(project),
                "location_state": project.location_state,
                "location_district": project.location_district,
                "location_city": project.location_city,
            },
            "overview": {
                "project_readiness_score": project_readiness,
                "approval_count": len(approval_cards),
                "approved": approval_status_counts.get("APPROVED", 0),
                "in_progress": sum(
                    approval_status_counts.get(s, 0)
                    for s in {
                        ApprovalStatus.SUBMITTED.value,
                        ApprovalStatus.UNDER_REVIEW.value,
                        ApprovalStatus.INSPECTION.value,
                    }
                ),
                "awaiting_applicant": sum(
                    approval_status_counts.get(s, 0) for s in _PRE_SUBMISSION_STATUSES
                ),
                "queries": sum(card["query"]["open_count"] for card in approval_cards),
                "inspections": len(upcoming_inspections),
                "high_risk": sum(1 for card in approval_cards if card["risk"].get("band") == "HIGH"),
                "sla_at_risk": sum(
                    1 for card in approval_cards if card["sla"].get("status") == "AT_RISK"
                ),
                "sla_breached": sum(
                    1 for card in approval_cards if card["sla"].get("status") == "BREACHED"
                ),
                "documents_total": documents["total"],
                "documents_attention": documents["needs_attention"],
                "compliance_score": compliance.get("score", 0),
                "renewals_due": len(compliance_alerts),
                "incentive_matches": len(incentives),
                "open_grievances": len(grievances),
                "action_count": action_count,
            },
            "profile": self._profile_summary(profile),
            "approvals": approval_cards,
            "roadmap": self._roadmap_summary(graph),
            "documents": documents,
            "compliance": {
                "score": compliance.get("score", 0),
                "on_track": sum(1 for item in compliance.get("items", []) if item.get("status") == "ON_TRACK"),
                "at_risk": sum(1 for item in compliance.get("items", []) if item.get("status") == "AT_RISK"),
                "overdue": sum(1 for item in compliance.get("items", []) if item.get("status") == "OVERDUE"),
                "renewals": compliance_alerts[:6],
            },
            "incentives": {
                "count": len(incentives),
                "top_matches": [
                    {
                        "id": match.get("scheme_id") or match.get("id"),
                        "name": match.get("name"),
                        "department": match.get("department"),
                        "match_score": match.get("match_score"),
                        "readiness_score": match.get("readiness_score"),
                        "readiness_state": match.get("readiness_state"),
                        "document_summary": match.get("document_summary"),
                        "match_reason": match.get("match_reason"),
                        "benefits": match.get("benefits", [])[:3],
                        "source_url": match.get("source_url"),
                    }
                    for match in incentives[:5]
                ],
                "disclaimer": "Scheme matches are based on the configured prototype catalogue and are not a guarantee of eligibility or benefit.",
            },
            "inspections": {
                "upcoming": upcoming_inspections[:6],
                "count": len(upcoming_inspections),
            },
            "grievances": {
                "open": len(grievances),
                "escalated": sum(1 for item in grievances if item["status"] == "ESCALATED"),
                "overdue_targets": sum(1 for item in grievances if item.get("overdue_target")),
                "items": grievances[:6],
            },
            "sla_risk": {
                "high_risk": risk_portfolio.get("high_risk", 0),
                "medium_risk": risk_portfolio.get("medium_risk", 0),
                "low_risk": risk_portfolio.get("low_risk", 0),
                "sla_on_track": risk_portfolio.get("sla_on_track", 0),
                "sla_at_risk": risk_portfolio.get("sla_at_risk", 0),
                "sla_breached": risk_portfolio.get("sla_breached", 0),
                "applications": risk_portfolio.get("applications", [])[:8],
            },
            "action_center": action_center,
            "metadata": {
                "generated_at": _utc_now_naive().isoformat() + "Z",
                "government_api_status": "not_connected",
                "disclaimer": (
                    "Unified command-center values compose configured prototype data and existing UDYOGSETU operational models. "
                    "SLA/risk estimates are advisory, scheme matches are catalogue-based, and government integrations are not live in this prototype. "
                    "This view does not make statutory determinations or guarantee government processing outcomes."
                ),
            },
        }

    async def _get_owned_project(self, project_id: UUID, user_id: UUID) -> Project:
        result = await self.db.execute(
            select(Project).where(Project.id == project_id, Project.user_id == user_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found or not owned by the current user")
        return project

    async def _get_profile(self, user_id: UUID) -> BusinessProfile | None:
        result = await self.db.execute(
            select(BusinessProfile).where(BusinessProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def _get_approvals(self, project_id: UUID) -> list[Approval]:
        result = await self.db.execute(
            select(Approval)
            .options(selectinload(Approval.documents))
            .where(Approval.project_id == project_id)
            .order_by(Approval.created_at.asc())
        )
        return list(result.scalars().all())

    async def _readiness_by_approval(self, approvals: list[Approval], project: Project) -> dict[str, dict]:
        service = SubmissionReadinessService(self.db)
        result: dict[str, dict] = {}
        for approval in approvals:
            if _status(approval.status) not in _PRE_SUBMISSION_STATUSES:
                continue
            try:
                result[str(approval.id)] = await service.evaluate(approval.id, project.user_id)
            except ValueError:
                continue
        return result

    async def _preparation_by_approval(self, approvals: list[Approval]) -> dict[UUID, dict]:
        ids = [approval.id for approval in approvals if _status(approval.status) in _PRE_SUBMISSION_STATUSES]
        if not ids:
            return {}
        result = await self.db.execute(
            select(ApplicationPreparation.approval_id, ApplicationPreparation.status, ApplicationPreparation.prepared_at)
            .where(ApplicationPreparation.approval_id.in_(ids))
        )
        return {
            row.approval_id: {
                "status": row.status,
                "prepared_at": row.prepared_at.isoformat() if row.prepared_at else None,
            }
            for row in result.all()
        }

    async def _query_signals(self, project_id: UUID) -> dict[UUID, int]:
        result = await self.db.execute(
            select(Approval.id, func.count(ApplicationQuery.id))
            .join(ApplicationQuery, ApplicationQuery.approval_id == Approval.id)
            .where(
                Approval.project_id == project_id,
                ApplicationQuery.status.in_(_ACTIVE_QUERY_STATUSES),
            )
            .group_by(Approval.id)
        )
        return {approval_id: int(count) for approval_id, count in result.all()}

    async def _inspection_signals(self, project_id: UUID) -> dict[UUID, dict]:
        result = await self.db.execute(
            select(
                inspection_visit_approvals.c.approval_id,
                Approval.name,
                InspectionVisit.id,
                InspectionVisit.scheduled_start,
                InspectionVisit.scheduled_end,
                InspectionVisit.location,
                InspectionVisit.status,
                InspectionVisit.assigned_officer_id,
            )
            .join(
                InspectionVisit,
                InspectionVisit.id == inspection_visit_approvals.c.inspection_visit_id,
            )
            .join(
                Approval,
                Approval.id == inspection_visit_approvals.c.approval_id,
            )
            .where(
                InspectionVisit.project_id == project_id,
                InspectionVisit.status.in_(_ACTIVE_INSPECTION_STATUSES),
            )
            .order_by(InspectionVisit.scheduled_start.asc())
        )
        mapping: dict[UUID, dict] = {}
        for row in result.all():
            entry = mapping.get(row.approval_id)
            if entry is None:
                entry = {
                    "scheduled": True,
                    "visit_id": str(row.id),
                    "scheduled_start": row.scheduled_start.isoformat() if row.scheduled_start else None,
                    "scheduled_end": row.scheduled_end.isoformat() if row.scheduled_end else None,
                    "location": row.location,
                    "status": row.status,
                    "assigned_officer_id": str(row.assigned_officer_id) if row.assigned_officer_id else None,
                    "approval_names": [],
                }
                mapping[row.approval_id] = entry
            if row.name and row.name not in entry["approval_names"]:
                entry["approval_names"].append(row.name)
        return mapping

    async def _grievances(self, project_id: UUID) -> list[dict]:
        result = await self.db.execute(
            select(Grievance)
            .where(
                Grievance.project_id == project_id,
                Grievance.status.in_(_ACTIVE_GRIEVANCE_STATUSES),
            )
            .order_by(Grievance.updated_at.desc(), Grievance.created_at.desc())
        )
        now = _utc_now_naive()
        items = []
        for grievance in result.scalars().all():
            overdue = bool(grievance.response_target_at and grievance.response_target_at < now)
            items.append(
                {
                    "id": str(grievance.id),
                    "approval_id": str(grievance.approval_id) if grievance.approval_id else None,
                    "application_id": grievance.application_id,
                    "subject": grievance.subject,
                    "priority": grievance.priority,
                    "status": grievance.status,
                    "escalation_level": grievance.escalation_level,
                    "response_target_at": grievance.response_target_at.isoformat() if grievance.response_target_at else None,
                    "overdue_target": overdue,
                    "created_at": grievance.created_at.isoformat() if grievance.created_at else None,
                }
            )
        return items

    async def _documents(self, project_id: UUID) -> dict:
        result = await self.db.execute(select(Document).where(Document.project_id == project_id))
        documents = list(result.scalars().all())
        statuses = Counter(_status(doc.status) for doc in documents)
        needs_attention = sum(
            1 for doc in documents if _status(doc.status) in {"WARNING", "REJECTED", "EXPIRED", "PROCESSING", "UPLOADED"}
        )
        return {
            "total": len(documents),
            "ready": statuses.get("VERIFIED", 0),
            "needs_attention": needs_attention,
            "by_status": dict(statuses),
        }

    async def _get_compliance_alerts(self, project_id: UUID) -> list[dict]:
        from app.services.compliance_tracker import ComplianceTracker

        tracker = ComplianceTracker(self.db)
        return await tracker.get_compliance_alerts(str(project_id))

    def _approval_card(
        self,
        approval: Approval,
        readiness: dict | None,
        preparation: dict | None,
        query_count: int,
        inspection: dict | None,
        risk: dict | None,
        compliance_alerts: list[dict],
    ) -> dict:
        status = _status(approval.status)
        sla = (risk or {}).get("sla") or {
            "status": "COMPLETED" if status == ApprovalStatus.APPROVED.value else "NOT_STARTED",
            "days_remaining": None,
            "days_elapsed": 0,
            "deadline": None,
        }
        readiness_state = readiness.get("readiness_state") if readiness else None
        preparation_status = preparation.get("status") if preparation else None
        renewal = next(
            (alert for alert in compliance_alerts if alert.get("approval_id") == str(approval.id)),
            None,
        )

        action_priority = "NONE"
        action = None
        if readiness_state == "BLOCKED":
            action_priority, action = "HIGH", "Resolve pre-submission blockers"
        elif query_count:
            action_priority, action = "HIGH", "Resolve department query"
        elif sla.get("status") == "BREACHED":
            action_priority, action = "HIGH", "Review SLA breach"
        elif readiness_state == "ACTION_REQUIRED":
            action_priority, action = "MEDIUM", "Complete readiness actions"
        elif sla.get("status") == "AT_RISK":
            action_priority, action = "MEDIUM", "Review before SLA deadline"
        elif inspection:
            action_priority, action = "INFO", "Confirm inspection details"
        elif renewal:
            action_priority, action = "MEDIUM", "Prepare renewal"

        return {
            "id": str(approval.id),
            "application_id": _approval_app_id(approval),
            "name": approval.name,
            "department": approval.department,
            "status": status,
            "mandatory": bool(approval.is_mandatory),
            "risk_level": approval.risk_level,
            "estimated_processing_days": approval.estimated_processing_days,
            "submitted_at": approval.submitted_at.isoformat() if approval.submitted_at else None,
            "approved_at": approval.approved_at.isoformat() if approval.approved_at else None,
            "sla": {
                "status": sla.get("status"),
                "days_elapsed": sla.get("days_elapsed"),
                "days_remaining": sla.get("days_remaining"),
                "deadline": sla.get("deadline"),
            },
            "risk": {
                "band": (risk or {}).get("risk_band"),
                "score": (risk or {}).get("risk_score"),
                "factors": (risk or {}).get("key_risk_factors", [])[:3],
            },
            "readiness": {
                "state": readiness_state,
                "score": readiness.get("score") if readiness else None,
                "blockers": len(readiness.get("blocking_issues", [])) if readiness else 0,
                "warnings": len(readiness.get("warnings", [])) if readiness else 0,
                "next_actions": [a.get("action") for a in (readiness.get("next_actions", []) if readiness else [])[:3]],
            },
            "preparation": {
                "status": preparation_status,
                "prepared_at": preparation.get("prepared_at") if preparation else None,
            },
            "query": {"open_count": query_count},
            "inspection": inspection or {"scheduled": False},
            "renewal": renewal,
            "action": {"priority": action_priority, "label": action},
        }

    def _build_action_center(
        self,
        project: Project,
        profile: BusinessProfile | None,
        approvals: list[dict],
        documents: dict,
        compliance: dict,
        compliance_alerts: list[dict],
        grievances: list[dict],
        incentives: list[dict],
    ) -> list[dict]:
        actions: list[dict] = []

        if profile is None:
            actions.append(self._action("profile.missing", "MEDIUM", "Set up Business Profile", "Create your reusable business profile before preparing applications.", "/dashboard/profile"))
        else:
            score = BusinessProfileService(self.db)._completeness(profile)["score"]
            if score < 100:
                actions.append(self._action("profile.incomplete", "MEDIUM", "Complete Business Profile", f"Profile is {score}% complete. Add missing business identity and address details.", "/dashboard/profile"))

        if documents["needs_attention"]:
            actions.append(self._action(
                "documents.attention",
                "MEDIUM",
                "Review document issues",
                f"{documents['needs_attention']} project document(s) need validation or attention.",
                f"/dashboard/{project.id}/documents",
            ))

        for approval in approvals:
            app_id = approval["application_id"]
            target = f"/dashboard/applications/{app_id}"
            if approval["readiness"]["state"] == "BLOCKED":
                actions.append(self._action(
                    f"readiness.{approval['id']}",
                    "HIGH",
                    f"Prepare {approval['name']}",
                    f"{approval['readiness']['blockers']} blocking readiness issue(s) remain before submission.",
                    f"/dashboard/applications/{app_id}/prepare",
                    approval["id"],
                ))
            if approval["query"]["open_count"]:
                actions.append(self._action(
                    f"query.{approval['id']}",
                    "HIGH",
                    f"Resolve {approval['name']} query",
                    "A department query is awaiting applicant response.",
                    f"{target}/query",
                    approval["id"],
                ))
            if approval["sla"]["status"] == "BREACHED":
                actions.append(self._action(
                    f"sla.breached.{approval['id']}",
                    "HIGH",
                    f"Review SLA breach — {approval['name']}",
                    "The configured processing window has elapsed; review the authorized follow-up or grievance path.",
                    target,
                    approval["id"],
                ))
            elif approval["sla"]["status"] == "AT_RISK":
                actions.append(self._action(
                    f"sla.risk.{approval['id']}",
                    "MEDIUM",
                    f"Monitor SLA — {approval['name']}",
                    "The application is approaching its configured processing window.",
                    target,
                    approval["id"],
                ))
            if approval["inspection"].get("scheduled"):
                actions.append(self._action(
                    f"inspection.{approval['id']}",
                    "INFO",
                    f"Confirm inspection — {approval['name']}",
                    f"Scheduled for {approval['inspection'].get('scheduled_start') or 'the configured time'}.",
                    "/dashboard/inspections",
                    approval["id"],
                ))
            if approval["renewal"]:
                action_type = "HIGH" if approval["renewal"].get("days_until_renewal", 999) < 0 else "MEDIUM"
                actions.append(self._action(
                    f"renewal.{approval['id']}",
                    action_type,
                    f"Prepare renewal — {approval['name']}",
                    "A renewal window is due or approaching based on the configured compliance cycle.",
                    f"/dashboard/{project.id}/compliance",
                    approval["id"],
                ))

        for grievance in grievances:
            if grievance.get("status") == "ESCALATED":
                actions.append(self._action(
                    f"grievance.escalated.{grievance['id']}",
                    "HIGH",
                    f"Follow up grievance — {grievance['subject']}",
                    f"Escalated to level {grievance.get('escalation_level', 0)}.",
                    f"/dashboard/grievances",
                    grievance["id"],
                ))
            elif grievance.get("overdue_target"):
                actions.append(self._action(
                    f"grievance.overdue.{grievance['id']}",
                    "MEDIUM",
                    f"Follow up grievance — {grievance['subject']}",
                    "Its internal response target has elapsed.",
                    "/dashboard/grievances",
                    grievance["id"],
                ))

        if compliance.get("score", 0) < 100 and compliance.get("items"):
            actions.append(self._action(
                "compliance.review",
                "MEDIUM",
                "Review compliance tasks",
                f"Current compliance score is {compliance.get('score', 0)}%.",
                f"/dashboard/{project.id}/compliance",
            ))

        if incentives:
            actions.append(self._action(
                "incentives.review",
                "INFO",
                "Review incentive matches",
                f"{len(incentives)} configured scheme match(es) are available for this project.",
                f"/dashboard/{project.id}/schemes",
            ))

        actions.sort(key=lambda item: {"HIGH": 3, "MEDIUM": 2, "INFO": 1}.get(item["priority"], 0), reverse=True)
        # Avoid overwhelming the dashboard; the linked domain pages contain the full detail.
        return actions[:12]

    @staticmethod
    def _action(action_id: str, priority: str, title: str, description: str, target: str, reference_id: str | None = None) -> dict:
        return {
            "id": action_id,
            "priority": priority,
            "title": title,
            "description": description,
            "target": target,
            "reference_id": reference_id,
        }

    @staticmethod
    def _profile_summary(profile: BusinessProfile | None) -> dict:
        if profile is None:
            return {
                "exists": False,
                "completeness_score": 0,
                "missing_fields": [],
                "identity_fields_present": 0,
                "verification": {},
            }
        completeness = BusinessProfileService._completeness(profile)
        return {
            "exists": True,
            "completeness_score": completeness["score"],
            "missing_fields": completeness["missing_fields"],
            "identity_fields_present": completeness["identity_fields_present"],
            "verification": BusinessProfileService._normalized_verification(profile),
        }

    @staticmethod
    def _roadmap_summary(graph: dict) -> dict:
        summary = graph.get("summary") or {}
        critical = graph.get("critical_path") or {}
        return {
            "total_count": summary.get("total_count", len(graph.get("nodes", []))),
            "sequential_duration_days": summary.get("sequential_duration_days", 0),
            "parallel_duration_days": summary.get("parallel_duration_days", 0),
            "time_saved_days": summary.get("theoretical_time_saved_days", 0),
            "parallel_group_count": summary.get("parallel_group_count", len(graph.get("parallel_groups", []))),
            "critical_path_days": critical.get("duration_days", 0),
            "critical_path_names": critical.get("names") or [a.get("name") for a in critical.get("approvals", [])],
            "warnings": graph.get("warnings", []),
        }

    @staticmethod
    def _project_data(project: Project) -> dict:
        return {
            "industry": project.industry,
            "sector": project.sector,
            "state": project.location_state,
            "location": project.location_state,
            "investment_amount": project.investment_amount,
            "employees": project.employees,
        }

    @staticmethod
    def _project_readiness_score(
        project: Project,
        profile: BusinessProfile | None,
        approvals: list[dict],
        compliance: dict,
    ) -> int:
        """Transparent operational readiness metric, not a statutory score."""
        profile_score = 0 if not profile else BusinessProfileService._completeness(profile)["score"]
        if approvals:
            approval_completion = round(
                sum(1 for approval in approvals if approval["status"] in _TERMINAL_APPROVALS) / len(approvals) * 100
            )
            pre_submit = [a["readiness"]["score"] for a in approvals if a["readiness"]["score"] is not None]
            readiness_score = round(sum(pre_submit) / len(pre_submit)) if pre_submit else 100
        else:
            approval_completion = 0
            readiness_score = 100
        compliance_score = compliance.get("score", 100) if compliance.get("items") else 100
        score = round(profile_score * 0.25 + approval_completion * 0.35 + readiness_score * 0.20 + compliance_score * 0.20)
        return max(0, min(100, score))
