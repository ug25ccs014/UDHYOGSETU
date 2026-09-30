from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Approval, ComplianceItem, Project, approval_documents



def _naive_utc(value: datetime) -> datetime:
    """Normalize aware/naive datetimes to the UTC-naive DB convention."""
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value

def _status_value(value) -> str:
    """Normalise a SQLAlchemy enum column value to its plain string form."""
    return value.value if hasattr(value, "value") else str(value)

class ComplianceTracker:
    """Track compliance status and requirements post-approval"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    @staticmethod
    def _as_uuid(value) -> UUID | None:
        """Coerce a string/UUID value to UUID, returning None when invalid."""
        try:
            return UUID(str(value))
        except (ValueError, AttributeError, TypeError):
            return None
    
    async def get_compliance_requirements(self, approval_id: str) -> dict:
        """
        Get compliance requirements for an approval
        """
        approval_uuid = self._as_uuid(approval_id)
        if not approval_uuid:
            return {}
        
        result = await self.db.execute(
            select(Approval).where(Approval.id == approval_uuid)
        )
        approval = result.scalar_one_or_none()
        
        if not approval:
            return {}
        
        # Define compliance requirements by approval type
        requirements = self._get_requirements_by_type(approval.name)
        
        return {
            "approval_id": str(approval.id),
            "approval_name": approval.name,
            "department": approval.department,
            "requirements": requirements,
            "renewal_cycle": self._get_renewal_cycle(approval.name),
        }
    
    def _get_requirements_by_type(self, approval_name: str) -> list:
        """Get compliance requirements based on approval type"""
        name_lower = approval_name.lower()
        
        if 'factory' in name_lower:
            return [
                "Quarterly workplace safety inspection",
                "Annual boiler inspection (if applicable)",
                "Monthly fire safety check",
                "Biannual employee training on safety",
                "Maintain accident register",
            ]
        
        elif 'mpcb' in name_lower or 'pollution' in name_lower:
            return [
                "Quarterly emission monitoring",
                "Monthly wastewater quality check",
                "Annual environmental audit",
                "Submit pollution control status report",
                "Maintain air quality monitoring log",
            ]
        
        elif 'boiler' in name_lower:
            return [
                "Annual boiler inspection",
                "Quarterly safety valve inspection",
                "Annual water quality testing",
                "Maintain boiler maintenance log",
                "Post pressure vessel tags",
            ]
        
        elif 'fire' in name_lower:
            return [
                "Monthly fire extinguisher check",
                "Quarterly fire drill",
                "Annual fire prevention audit",
                "Maintain fire safety training records",
                "Update fire safety plan",
            ]
        
        elif 'labour' in name_lower:
            return [
                "Quarterly wage register review",
                "Annual employee training",
                "Maintain attendance records",
                "Submit ESI/PF returns",
                "Annual occupational health check",
            ]
        
        return [
            "Regular documentation review",
            "Annual compliance audit",
            "Maintain records and logs",
        ]
    
    def _get_renewal_cycle(self, approval_name: str) -> dict:
        """Get renewal cycle for approval"""
        name_lower = approval_name.lower()
        
        cycles = {
            'factory': {'months': 12, 'advance_notice_days': 60},
            'mpcb': {'months': 5, 'advance_notice_days': 120},
            'boiler': {'months': 12, 'advance_notice_days': 90},
            'fire': {'months': 12, 'advance_notice_days': 60},
            'labour': {'months': 12, 'advance_notice_days': 45},
        }
        
        for key, cycle in cycles.items():
            if key in name_lower:
                return cycle
        
        return {'months': 12, 'advance_notice_days': 90}
    
    async def get_compliance_score(self, project_id: str) -> dict:
        """
        Calculate overall compliance score for a project
        """
        project_uuid = self._as_uuid(project_id)
        if not project_uuid:
            return {"score": 0}
        
        result = await self.db.execute(
            select(Project).where(Project.id == project_uuid)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            return {"score": 0}

        from app.services.compliance import ComplianceService
        await ComplianceService(self.db).ensure_compliance_items(project_uuid)

        # Get all approvals
        approvals_result = await self.db.execute(
            select(Approval).where(Approval.project_id == project_uuid)
        )
        approvals = approvals_result.scalars().all()

        # Get compliance items for adherence/timeliness metrics
        items_result = await self.db.execute(
            select(ComplianceItem).where(ComplianceItem.project_id == project_uuid)
        )
        items = items_result.scalars().all()

        # Calculate scores
        scores = {
            'approval_status': 0,
            'document_completeness': 0,
            'compliance_adherence': 0,
            'timeliness': 0,
        }

        if not approvals:
            return {"score": 0, "components": scores}

        # Score based on approval status
        approved = sum(1 for a in approvals if _status_value(a.status) == "APPROVED")
        scores['approval_status'] = (approved / len(approvals)) * 100

        # Score based on document completeness: approvals that have at least
        # one document attached through the approval_documents association.
        docs_result = await self.db.execute(
            select(approval_documents.c.approval_id)
            .where(approval_documents.c.approval_id.in_([a.id for a in approvals]))
            .distinct()
        )
        approvals_with_docs = {row[0] for row in docs_result.all()}
        docs_complete = sum(1 for a in approvals if a.id in approvals_with_docs)
        scores['document_completeness'] = round((docs_complete / len(approvals)) * 100, 2)

        # Score based on compliance items (derived, not mocked)
        if items:
            on_track = sum(1 for i in items if _status_value(i.status) == "ON_TRACK")
            scores['compliance_adherence'] = round((on_track / len(items)) * 100, 2)
            not_overdue = sum(1 for i in items if _status_value(i.status) in ("ON_TRACK", "AT_RISK"))
            scores['timeliness'] = round((not_overdue / len(items)) * 100, 2)
        
        # Weighted average
        weights = {
            'approval_status': 0.35,
            'document_completeness': 0.25,
            'compliance_adherence': 0.25,
            'timeliness': 0.15,
        }
        
        total_score = sum(
            scores[key] * weights[key]
            for key in scores
        )
        
        return {
            "project_id": str(project_id),
            "score": round(total_score, 2),
            "components": scores,
            "grade": self._score_to_grade(total_score),
            "last_updated": datetime.utcnow().isoformat(),
        }
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to grade"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    async def get_compliance_alerts(self, project_id: str) -> list:
        """
        Get compliance alerts for a project
        """
        alerts = []
        approval_uuid = self._as_uuid(project_id)
        if not approval_uuid:
            return alerts

        # Get all approvals
        result = await self.db.execute(
            select(Approval).where(Approval.project_id == approval_uuid)
        )
        approvals = result.scalars().all()

        now = datetime.utcnow()

        for approval in approvals:
            if _status_value(approval.status) != 'APPROVED':
                continue

            renewal_cycle = self._get_renewal_cycle(approval.name)
            advance_notice = renewal_cycle.get('advance_notice_days', 90)
            renewal_days = approval.renewal_period_days or renewal_cycle.get('months', 12) * 30

            if approval.approved_at:
                renewal_date = _naive_utc(approval.approved_at) + timedelta(days=renewal_days)
                days_until_renewal = (renewal_date - now).days

                if -advance_notice <= days_until_renewal <= advance_notice:
                    alerts.append({
                        "type": "renewal_overdue" if days_until_renewal < 0 else "renewal_due",
                        "approval_id": str(approval.id),
                        "approval_name": approval.name,
                        "days_until_renewal": days_until_renewal,
                        "severity": "high" if days_until_renewal <= 30 else "medium",
                    })

        return alerts
