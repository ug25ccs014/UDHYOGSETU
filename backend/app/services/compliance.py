from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Approval, ApprovalStatus, ComplianceItem, ComplianceStatus


def _status_value(value) -> str:
    """Normalise a SQLAlchemy enum column value to its plain string form."""
    return value.value if hasattr(value, "value") else str(value)


class ComplianceService:
    """Compliance management service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def ensure_compliance_items(self, project_id: UUID) -> None:
        """Materialize derived compliance requirements for APPROVED approvals.

        Compliance requirements for an approval are deterministic (derived from
        the approval type), but they used to only be computed on the fly for
        display. This method persists them as ``ComplianceItem`` rows so the
        score/adherence math has real data. Idempotent: rows already present for
        a (project, category, requirement) pair are left untouched.
        """
        from app.services.compliance_tracker import ComplianceTracker

        result = await self.db.execute(
            select(Approval).where(
                Approval.project_id == project_id,
                Approval.status == ApprovalStatus.APPROVED,
            )
        )
        approvals = result.scalars().all()
        if not approvals:
            return

        existing_result = await self.db.execute(
            select(ComplianceItem).where(ComplianceItem.project_id == project_id)
        )
        existing = existing_result.scalars().all()
        seen = {(item.category, item.requirement) for item in existing}

        tracker = ComplianceTracker(self.db)
        now = datetime.utcnow()
        added = False
        for approval in approvals:
            cycle = tracker._get_renewal_cycle(approval.name)
            renewal_days = approval.renewal_period_days or cycle.get("months", 12) * 30
            base_date = approval.approved_at or now
            for requirement in tracker._get_requirements_by_type(approval.name):
                key = (approval.name, requirement)
                if key in seen:
                    continue
                self.db.add(
                    ComplianceItem(
                        project_id=project_id,
                        category=approval.name,
                        requirement=requirement,
                        frequency=None,
                        due_date=base_date + timedelta(days=renewal_days),
                        next_due=base_date + timedelta(days=renewal_days),
                        status=ComplianceStatus.ON_TRACK,
                        source="auto-seeded",
                    )
                )
                seen.add(key)
                added = True

        if added:
            await self.db.commit()

    async def get_compliance_dashboard(self, project_id: UUID) -> dict:
        """Get compliance dashboard with scores and metrics."""
        await self.ensure_compliance_items(project_id)

        result = await self.db.execute(
            select(ComplianceItem).where(ComplianceItem.project_id == project_id)
        )
        items = result.scalars().all()

        if not items:
            return {
                "project_id": str(project_id),
                "score": 0,
                "overall_score": 0,
                "categories": {},
                "items": [],
                "items_count": 0,
            }

        categories = {}
        for item in items:
            if item.category not in categories:
                categories[item.category] = {"total": 0, "compliant": 0}

            categories[item.category]["total"] += 1
            if _status_value(item.status) == "ON_TRACK":
                categories[item.category]["compliant"] += 1

        total = sum(c["total"] for c in categories.values())
        compliant = sum(c["compliant"] for c in categories.values())
        score = round((compliant / total) * 100, 2) if total else 0

        return {
            "project_id": str(project_id),
            "score": score,
            "overall_score": score,
            "categories": categories,
            "items": [
                {
                    "id": str(item.id),
                    "category": item.category,
                    "requirement": item.requirement,
                    "status": _status_value(item.status),
                    "due_date": item.due_date.isoformat() if item.due_date else None,
                    "next_due": item.next_due.isoformat() if item.next_due else None,
                }
                for item in items
            ],
            "items_count": len(items),
        }

    async def get_compliance_items(self, project_id: UUID) -> list[ComplianceItem]:
        """Get all compliance items for a project"""
        await self.ensure_compliance_items(project_id)
        result = await self.db.execute(
            select(ComplianceItem).where(ComplianceItem.project_id == project_id)
        )
        return result.scalars().all()