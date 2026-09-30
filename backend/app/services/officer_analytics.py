"""Officer/administrator analytics.

Aggregates data across all projects and approvals to surface department
bottlenecks, SLA performance, and application throughput for the officer
dashboard.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ApplicationQuery,
    Approval,
    ApprovalStatus,
    Grievance,
    InspectionVisit,
    InspectionVisitStatus,
)


class OfficerAnalyticsService:
    """Compute cross-system officer-level metrics."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _all_approvals(self) -> list:
        rows = await self.db.execute(select(Approval))
        return list(rows.scalars().all())

    async def overview(self) -> dict:
        approvals = await self._all_approvals()
        total = len(approvals)
        pending = [a for a in approvals if a.status.value not in ("APPROVED", "REJECTED")]
        breached = []
        for a in pending:
            sla = a.estimated_processing_days or 60
            base = a.submitted_at or a.created_at
            if not base:
                continue
            elapsed = max(0, (datetime.now(timezone.utc) - _as_utc(base)).days)
            if elapsed > sla:
                breached.append(a)

        processing = [elapsed_days(a) for a in approvals if a.status.value == "APPROVED"]
        avg = round(sum(processing) / len(processing), 1) if processing else 0

        return {
            "total_applications": total,
            "pending_review": len(pending),
            "sla_breaches": len(breached),
            "avg_processing_days": avg,
            "approved": sum(1 for a in approvals if a.status.value == "APPROVED"),
        }

    async def by_department(self) -> list[dict]:
        approvals = await self._all_approvals()
        by_dept: dict[str, dict] = {}
        for a in approvals:
            d = a.department or "Unknown"
            entry = by_dept.setdefault(d, {"department": d, "total": 0, "approved": 0, "pending": 0, "sla_breaches": 0, "avg_days": []})
            entry["total"] += 1
            status = a.status.value
            if status == "APPROVED":
                entry["approved"] += 1
                entry["avg_days"].append(elapsed_days(a))
            elif status in ("APPROVED", "REJECTED"):
                pass
            else:
                entry["pending"] += 1
            sla = a.estimated_processing_days or 60
            base = a.submitted_at or a.created_at
            if a.status.value not in ("APPROVED", "REJECTED") and base and (datetime.now(timezone.utc) - _as_utc(base)).days > sla:
                entry["sla_breaches"] += 1

        result = []
        for entry in by_dept.values():
            entry["avg_days"] = round(sum(entry["avg_days"]) / len(entry["avg_days"]), 1) if entry["avg_days"] else 0
            entry["backlog"] = entry["pending"]
            result.append(entry)
        result.sort(key=lambda e: (e["sla_breaches"], e["pending"]), reverse=True)
        return result

    async def status_distribution(self) -> list[dict]:
        approvals = await self._all_approvals()
        counts: dict[str, int] = {}
        for a in approvals:
            s = a.status.value
            counts[s] = counts.get(s, 0) + 1
        return [{"status": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: -x[1])]

    async def command_center(
        self,
        department: str | None = None,
        risk_band: str | None = None,
        limit: int = 25,
    ) -> dict:
        """Compose live officer workload, risk queue and bottleneck signals.

        The service composes existing analytics and SLA-risk engines rather than
        introducing another application/risk source of truth. All returned
        operational signals are advisory and derived from persisted application
        state.
        """
        from app.services.sla_risk import SlaRiskService

        overview = await self.overview()
        departments = await self.by_department()
        distribution = await self.status_distribution()

        # Pull one unfiltered risk snapshot so aggregate signals remain stable
        # even when the officer applies a queue filter in the UI.
        all_risk = await SlaRiskService(self.db).officer_queue(limit=200)
        all_records = list(all_risk.get("applications", []))
        filtered_records = all_records
        if department:
            needle = department.strip().lower()
            filtered_records = [
                record for record in filtered_records
                if needle in str(record.get("department") or "").lower()
            ]
        if risk_band:
            band = risk_band.upper()
            filtered_records = [record for record in filtered_records if record.get("risk_band") == band]
        filtered_records.sort(key=self._queue_key, reverse=True)

        operational = await self._operational_counts()
        throughput = await self._throughput()
        distribution_counts = {item["status"]: item["count"] for item in distribution}
        review_queue_count = sum(
            distribution_counts.get(status, 0)
            for status in {
                ApprovalStatus.SUBMITTED.value,
                ApprovalStatus.UNDER_REVIEW.value,
                ApprovalStatus.QUERY_RAISED.value,
                ApprovalStatus.INSPECTION.value,
            }
        )
        awaiting_applicant = sum(
            distribution_counts.get(status, 0)
            for status in {ApprovalStatus.NOT_STARTED.value, ApprovalStatus.DRAFT.value}
        )
        bottlenecks = self._bottlenecks(
            distribution_counts,
            open_queries=operational["open_queries"],
            scheduled_inspections=operational["scheduled_inspections"],
            sla_breaches=overview["sla_breaches"],
        )

        return {
            "scope": "OFFICER",
            "overview": {
                **overview,
                "rejected": next((item["count"] for item in distribution if item["status"] == ApprovalStatus.REJECTED.value), 0),
                "high_risk": all_risk.get("high_risk", 0),
                "medium_risk": all_risk.get("medium_risk", 0),
                "action_required": all_risk.get("action_required", 0),
                "review_queue_count": review_queue_count,
                "awaiting_applicant": awaiting_applicant,
                "sla_on_track": all_risk.get("sla_on_track", 0),
                "sla_at_risk": all_risk.get("sla_at_risk", 0),
                "sla_breached": all_risk.get("sla_breached", 0),
                **operational,
            },
            "throughput": throughput,
            "departments": departments,
            "distribution": distribution,
            "bottlenecks": bottlenecks,
            "priority_queue": filtered_records[: max(1, min(limit, 200))],
            "filters": {
                "department": department,
                "risk_band": risk_band,
                "limit": limit,
            },
            "disclaimer": (
                "Operational dashboard metrics are calculated from the UDYOGSETU database. "
                "Risk indicators are predictive assistance, not statutory determinations or official government ratings."
            ),
        }

    async def _throughput(self) -> dict:
        """Count actual submitted applications in today/7-day/30-day windows."""
        approvals = await self._all_approvals()
        now = datetime.now(timezone.utc)
        starts = {
            "today": now.replace(hour=0, minute=0, second=0, microsecond=0),
            "week": now - timedelta(days=7),
            "month": now - timedelta(days=30),
        }
        submitted = [a for a in approvals if a.submitted_at]
        def in_window(a, start):
            base = _as_utc(a.submitted_at)
            return base is not None and base >= start
        return {
            "submissions_today": sum(1 for a in submitted if in_window(a, starts["today"])),
            "submissions_7d": sum(1 for a in submitted if in_window(a, starts["week"])),
            "submissions_30d": sum(1 for a in submitted if in_window(a, starts["month"])),
        }

    async def _operational_counts(self) -> dict:
        """Count open operational signals surfaced by Steps 6–9."""
        query_result = await self.db.execute(
            select(func.count(ApplicationQuery.id)).where(
                ApplicationQuery.status.in_(("OPEN", "DRAFT", "READY"))
            )
        )
        inspection_result = await self.db.execute(
            select(func.count(InspectionVisit.id)).where(
                InspectionVisit.status == InspectionVisitStatus.SCHEDULED.value
            )
        )
        grievance_result = await self.db.execute(
            select(func.count(Grievance.id)).where(
                Grievance.status.in_(("OPEN", "ACKNOWLEDGED", "IN_REVIEW", "ESCALATED"))
            )
        )
        return {
            "open_queries": int(query_result.scalar() or 0),
            "scheduled_inspections": int(inspection_result.scalar() or 0),
            "open_grievances": int(grievance_result.scalar() or 0),
        }

    @staticmethod
    def _queue_key(record: dict) -> tuple:
        sla = record.get("sla") or {}
        band_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        sla_order = {"BREACHED": 3, "AT_RISK": 2, "ON_TRACK": 1}
        return (
            sla_order.get(sla.get("status"), 0),
            band_order.get(record.get("risk_band"), 0),
            float(record.get("breach_probability") or 0),
            -float(sla.get("days_remaining") or 0),
        )

    @staticmethod
    def _bottlenecks(
        distribution_counts: dict[str, int],
        *,
        open_queries: int,
        scheduled_inspections: int,
        sla_breaches: int,
    ) -> list[dict]:
        """Return global, explainable workflow bottleneck signals. Counts can overlap."""
        active = sum(
            distribution_counts.get(status, 0)
            for status in {
                ApprovalStatus.SUBMITTED.value,
                ApprovalStatus.UNDER_REVIEW.value,
                ApprovalStatus.QUERY_RAISED.value,
                ApprovalStatus.INSPECTION.value,
            }
        )
        reasons = [
            ("Department review", distribution_counts.get("UNDER_REVIEW", 0), "Applications waiting in the department review stage."),
            ("Applicant query response", max(open_queries, distribution_counts.get("QUERY_RAISED", 0)), "Open query signals that require applicant or review action."),
            ("Inspection pending", max(scheduled_inspections, distribution_counts.get("INSPECTION", 0)), "Applications or visits waiting around inspection processing."),
            ("Submitted intake", distribution_counts.get("SUBMITTED", 0), "Submitted applications not yet moved into a later workflow stage."),
            ("SLA overdue", sla_breaches, "Applications beyond their configured processing window."),
        ]
        denominator = max(active, 1)
        out = []
        for name, count, description in reasons:
            if count <= 0:
                continue
            out.append({
                "name": name,
                "count": count,
                "share_percent": round((count / denominator) * 100, 1),
                "description": description,
                "overlap_possible": True,
            })
        out.sort(key=lambda item: (-item["count"], item["name"]))
        return out



def elapsed_days(approval) -> int:
    base = approval.submitted_at or approval.created_at
    if not base:
        return 0
    return max(0, (datetime.now(timezone.utc) - _as_utc(base)).days)


def _as_utc(dt):
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)