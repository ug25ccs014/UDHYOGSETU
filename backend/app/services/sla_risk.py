"""SLA + smart-risk orchestration for applicant and officer views.

This service deliberately builds on :class:`SlaEngine` and :class:`SlaPredictor`.
It adds transparent operational signals from persisted query, inspection and
application-document state without changing statutory workflow decisions.

All risk values are predictive/operational assistance, never a government
adjudication or official SLA determination.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ApplicationQuery,
    Approval,
    ApprovalStatus,
    Document,
    GovernmentApplication,
    InspectionVisit,
    InspectionVisitStatus,
    Project,
    approval_documents,
    inspection_visit_approvals,
)
from app.services.sla_engine import SlaEngine
from app.services.sla_predictor import SlaPredictor


_TERMINAL = {
    ApprovalStatus.APPROVED.value,
    ApprovalStatus.REJECTED.value,
    ApprovalStatus.EXPIRED.value,
    ApprovalStatus.CANCELED.value,
}
_ACTIVE_RISK_STATUSES = {
    ApprovalStatus.SUBMITTED.value,
    ApprovalStatus.UNDER_REVIEW.value,
    ApprovalStatus.QUERY_RAISED.value,
    ApprovalStatus.INSPECTION.value,
}
_DOCUMENT_WARNING_STATUSES = {"WARNING", "REJECTED", "EXPIRED", "PROCESSING", "UPLOADED"}
_QUERY_ACTIVE_STATUSES = {"OPEN", "DRAFT", "READY"}
_ACTIVE_INSPECTION_STATUSES = {InspectionVisitStatus.SCHEDULED.value}


def _status(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class SlaRiskService:
    """Compose deterministic SLA state and transparent operational risk signals."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.sla = SlaEngine()
        self.predictor = SlaPredictor(self.sla)

    async def evaluate_approval(self, approval: Approval, project: Project | None = None) -> dict:
        """Return a single enriched SLA/risk record."""
        prediction = self.predictor.predict(approval)
        sla_status = prediction.get("status", "NOT_STARTED")

        query_count, latest_query = await self._query_signal(approval.id)
        inspection = await self._inspection_signal(approval.id)
        document_issues = await self._document_issue_count(approval.id)
        government = await self._government_signal(approval.id)

        base_probability = float(prediction.get("breach_probability") or 0.0)
        adjusted_probability = self._adjust_probability(
            approval_status=_status(approval.status),
            base_probability=base_probability,
            query_count=query_count,
            inspection=inspection,
            document_issues=document_issues,
        )
        risk_band = self._risk_band(adjusted_probability, sla_status)

        factors = list(prediction.get("key_risk_factors") or [])
        if query_count and _status(approval.status) != ApprovalStatus.QUERY_RAISED.value:
            factors.append(f"Open applicant query ({query_count})")
        if inspection.get("scheduled") and _status(approval.status) != ApprovalStatus.INSPECTION.value:
            factors.append("Inspection scheduled")
        if document_issues:
            factors.append(f"{document_issues} application document issue(s)")
        factors = self._dedupe(factors)

        actions = self._recommendations(
            sla_status=sla_status,
            risk_band=risk_band,
            query_count=query_count,
            inspection=inspection,
            document_issues=document_issues,
        )

        return {
            "approval_id": str(approval.id),
            "application_id": approval.application_id or str(approval.id),
            "approval_name": approval.name,
            "department": approval.department,
            "project_id": str(approval.project_id),
            "project_name": project.name if project else None,
            "company_name": project.company_name if project else None,
            "project_location": ", ".join(
                part for part in [
                    project.location_city if project else None,
                    project.location_district if project else None,
                    project.location_state if project else None,
                ]
                if part
            ) or None,
            "status": _status(approval.status),
            "risk_band": risk_band,
            "risk_score": round(adjusted_probability * 100),
            "breach_probability": round(adjusted_probability, 3),
            "sla": {
                "status": sla_status,
                "sla_days": prediction.get("sla_days", approval.estimated_processing_days or 60),
                "days_elapsed": prediction.get("days_elapsed", 0),
                "days_remaining": prediction.get("days_remaining", 0),
                "deadline": prediction.get("deadline"),
                "reason": prediction.get("reason", ""),
            },
            "signals": {
                "query_open_count": query_count,
                "latest_query_id": str(latest_query.id) if latest_query else None,
                "inspection_scheduled": bool(inspection.get("scheduled")),
                "inspection_status": inspection.get("status"),
                "next_inspection_start": inspection.get("next_start"),
                "document_issue_count": document_issues,
                "government_system": government.get("system"),
                "government_source": government.get("source", "not_connected"),
            },
            "key_risk_factors": factors or ["No material operational risk signals identified"],
            "recommended_actions": actions,
            "confidence": prediction.get("confidence", 0.0),
            "predictive_assistance": True,
            "disclaimer": (
                "Operational risk assistance based on configured SLA rules and persisted application signals. "
                "It is not a statutory determination, official government risk score, or guarantee of processing time."
            ),
        }

    async def portfolio(self, user_id: UUID, project_id: UUID | None = None) -> dict:
        """Applicant-facing SLA/risk view across the user's projects."""
        stmt = (
            select(Approval, Project)
            .join(Project, Project.id == Approval.project_id)
            .where(Project.user_id == user_id)
            .order_by(Approval.updated_at.desc())
        )
        if project_id:
            stmt = stmt.where(Approval.project_id == project_id)
        rows = list((await self.db.execute(stmt)).all())

        records = [await self.evaluate_approval(approval, project) for approval, project in rows]
        records = [r for r in records if r["status"] in _ACTIVE_RISK_STATUSES]
        records.sort(key=self._queue_key, reverse=True)
        return self._aggregate(records, scope="PROJECT" if project_id else "PORTFOLIO")

    async def officer_queue(
        self,
        department: str | None = None,
        risk_band: str | None = None,
        limit: int = 50,
    ) -> dict:
        """Officer/admin queue sorted by urgency without changing workflow state."""
        stmt = select(Approval, Project).join(Project, Project.id == Approval.project_id).order_by(Approval.updated_at.desc())
        if department:
            stmt = stmt.where(Approval.department.ilike(f"%{department}%"))
        rows = list((await self.db.execute(stmt)).all())

        records = [await self.evaluate_approval(approval, project) for approval, project in rows]
        records = [r for r in records if r["status"] in _ACTIVE_RISK_STATUSES]
        if risk_band:
            records = [r for r in records if r["risk_band"] == risk_band.upper()]

        records.sort(key=self._queue_key, reverse=True)
        return {
            **self._aggregate(records, scope="OFFICER"),
            "applications": records[: max(1, min(limit, 200))],
            "filters": {"department": department, "risk_band": risk_band, "limit": limit},
        }

    @staticmethod
    def _aggregate(records: list[dict], scope: str) -> dict:
        risk_counts = Counter(record["risk_band"] for record in records)
        sla_counts = Counter(record["sla"]["status"] for record in records)
        actionable = [
            record for record in records
            if record["risk_band"] in {"HIGH", "MEDIUM"} or record["sla"]["status"] in {"AT_RISK", "BREACHED"}
        ]
        return {
            "scope": scope,
            "total_applications": len(records),
            "high_risk": risk_counts.get("HIGH", 0),
            "medium_risk": risk_counts.get("MEDIUM", 0),
            "low_risk": risk_counts.get("LOW", 0),
            "sla_on_track": sla_counts.get("ON_TRACK", 0),
            "sla_at_risk": sla_counts.get("AT_RISK", 0),
            "sla_breached": sla_counts.get("BREACHED", 0),
            "action_required": len(actionable),
            "applications": records,
        }

    async def _query_signal(self, approval_id: UUID) -> tuple[int, ApplicationQuery | None]:
        result = await self.db.execute(
            select(ApplicationQuery)
            .where(
                ApplicationQuery.approval_id == approval_id,
                ApplicationQuery.status.in_(_QUERY_ACTIVE_STATUSES),
            )
            .order_by(ApplicationQuery.updated_at.desc())
        )
        rows = list(result.scalars().all())
        return len(rows), rows[0] if rows else None

    async def _inspection_signal(self, approval_id: UUID) -> dict:
        stmt = (
            select(InspectionVisit)
            .join(
                inspection_visit_approvals,
                inspection_visit_approvals.c.inspection_visit_id == InspectionVisit.id,
            )
            .where(
                inspection_visit_approvals.c.approval_id == approval_id,
                InspectionVisit.status.in_(_ACTIVE_INSPECTION_STATUSES),
            )
            .order_by(InspectionVisit.scheduled_start.asc())
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        visit = rows[0] if rows else None
        return {
            "scheduled": visit is not None,
            "status": _status(visit.status) if visit else None,
            "next_start": visit.scheduled_start.isoformat() if visit else None,
        }

    async def _document_issue_count(self, approval_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count(Document.id))
            .select_from(Document)
            .join(approval_documents, approval_documents.c.document_id == Document.id)
            .where(
                approval_documents.c.approval_id == approval_id,
                Document.status.in_(_DOCUMENT_WARNING_STATUSES),
            )
        )
        return int(result.scalar_one() or 0)

    async def _government_signal(self, approval_id: UUID) -> dict:
        result = await self.db.execute(
            select(GovernmentApplication)
            .where(GovernmentApplication.approval_id == approval_id)
            .order_by(GovernmentApplication.updated_at.desc())
        )
        record = result.scalars().first()
        if not record:
            return {"system": None, "source": "not_connected"}
        return {"system": record.system, "source": "prototype_gateway_sync"}

    @staticmethod
    def _adjust_probability(
        *,
        approval_status: str,
        base_probability: float,
        query_count: int,
        inspection: dict,
        document_issues: int,
    ) -> float:
        score = base_probability
        # Predictor already accounts for QUERY_RAISED / INSPECTION statuses.
        if query_count and approval_status != ApprovalStatus.QUERY_RAISED.value:
            score += min(0.08, query_count * 0.04)
        if inspection.get("scheduled") and approval_status != ApprovalStatus.INSPECTION.value:
            score += 0.04
        if document_issues:
            score += min(0.06, document_issues * 0.02)
        return min(0.99, score)

    @staticmethod
    def _risk_band(probability: float, sla_status: str) -> str:
        if sla_status == "BREACHED" or probability >= 0.70:
            return "HIGH"
        if sla_status == "AT_RISK" or probability >= 0.35:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _recommendations(
        *,
        sla_status: str,
        risk_band: str,
        query_count: int,
        inspection: dict,
        document_issues: int,
    ) -> list[str]:
        actions: list[str] = []
        if sla_status == "BREACHED":
            actions.append("Review the application immediately and follow the authorized escalation path.")
        elif sla_status == "AT_RISK":
            actions.append("Review the case before the configured SLA deadline is reached.")
        if query_count:
            actions.append("Check the Query & Response Center for outstanding applicant evidence or response actions.")
        if inspection.get("scheduled"):
            actions.append("Confirm the scheduled inspection details and required site documents.")
        if document_issues:
            actions.append("Review flagged application documents before further processing.")
        if not actions and risk_band == "LOW":
            actions.append("Continue routine monitoring; no immediate intervention is indicated by this model.")
        return actions

    @staticmethod
    def _queue_key(record: dict) -> tuple[int, float, float]:
        risk_rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(record["risk_band"], 0)
        sla_rank = {"BREACHED": 3, "AT_RISK": 2, "ON_TRACK": 1, "NOT_STARTED": 0, "COMPLETED": 0}.get(
            record["sla"]["status"], 0
        )
        return risk_rank, sla_rank, float(record.get("breach_probability") or 0.0)

    @staticmethod
    def _dedupe(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out
