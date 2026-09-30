"""Deterministic SIH demo readiness inspection.

This service is read-only. It verifies that the seeded demo story exists and
returns actionable checks for the demo operator; it never mutates data or calls
a government system.
"""
from __future__ import annotations

from sqlalchemy import func, select

from app.models import (
    Approval, ApprovalStatus, ApplicationPreparation, BusinessProfile, Grievance, IncentiveApplicationCase,
    InspectionVisit, InspectionVisitStatus, KnowledgeDocument, Notification, Project,
)
from app.services.business_profile import BusinessProfileService
from app.services.gateway_service import GatewayService

DEMO_PROJECT_NAME = "ABC Textiles Pvt Ltd - New Dyes Unit"


class DemoReadinessService:
    def __init__(self, db):
        self.db = db

    async def inspect(self, user_id) -> dict:
        project_result = await self.db.execute(
            select(Project).where(Project.user_id == user_id, Project.name == DEMO_PROJECT_NAME).limit(1)
        )
        project = project_result.scalar_one_or_none()
        checks: list[dict] = []

        def add(key, label, ok, detail, href):
            checks.append({"key": key, "label": label, "ok": bool(ok), "detail": detail, "href": href})

        add("project", "Demo project", bool(project), "ABC Textiles demo project is available." if project else "Seed the demo dataset first.", "/dashboard" if not project else f"/dashboard/{project.id}")
        profile = None
        if project:
            profile = (await self.db.execute(select(BusinessProfile).where(BusinessProfile.user_id == user_id).limit(1))).scalar_one_or_none()
        completeness = BusinessProfileService._completeness(profile) if profile else {"score": 0, "missing": []}
        add("profile", "Business profile", completeness.get("score", 0) >= 80, f"Profile completeness: {completeness.get('score', 0)}%.", "/dashboard/profile")

        approvals = []
        if project:
            approvals = (await self.db.execute(select(Approval).where(Approval.project_id == project.id))).scalars().all()
        add("approvals", "Approval roadmap", len(approvals) >= 4, f"{len(approvals)} applicable approvals seeded.", f"/dashboard/{project.id}/approvals" if project else "/dashboard")
        has_query = any(a.status == ApprovalStatus.QUERY_RAISED for a in approvals)
        query_approval = next((a for a in approvals if a.status == ApprovalStatus.QUERY_RAISED), None)
        add("query", "Query Center", has_query, "A prototype department query is available." if has_query else "No seeded query found.", f"/dashboard/applications/{query_approval.application_id}/query" if query_approval and query_approval.application_id else "/dashboard/applications")

        preparation = None
        if project:
            preparation = (await self.db.execute(
                select(ApplicationPreparation).join(Approval, ApplicationPreparation.approval_id == Approval.id)
                .where(Approval.project_id == project.id)
                .limit(1)
            )).scalar_one_or_none()
        prep_approval = next((a for a in approvals if preparation and str(a.id) == str(preparation.approval_id)), None)
        add("preparation", "Application preparation", bool(preparation), "A reusable prefilled application draft is available." if preparation else "No seeded application-preparation draft found.", f"/dashboard/applications/{prep_approval.application_id}/prepare" if prep_approval and prep_approval.application_id else "/dashboard/applications")

        visit = None
        if project:
            visit = (await self.db.execute(select(InspectionVisit).where(InspectionVisit.project_id == project.id, InspectionVisit.status == InspectionVisitStatus.SCHEDULED.value).order_by(InspectionVisit.scheduled_start).limit(1))).scalar_one_or_none()
        add("inspection", "Inspection planner", bool(visit), "A scheduled prototype inspection is available." if visit else "No scheduled demo inspection found.", "/dashboard/inspections")

        grievance = None
        if project:
            grievance = (await self.db.execute(select(Grievance).where(Grievance.user_id == user_id, Grievance.project_id == project.id).order_by(Grievance.created_at.desc()).limit(1))).scalar_one_or_none()
        add("grievance", "Grievance workflow", bool(grievance), "An auditable prototype grievance is available." if grievance else "No seeded grievance found.", "/dashboard/grievances")

        unread = await self.db.execute(select(func.count(Notification.id)).where(Notification.user_id == user_id, Notification.is_read.is_(False)))
        unread_count = int(unread.scalar_one() or 0)
        add("notifications", "Notification inbox", unread_count > 0, f"{unread_count} unread notification(s).", "/dashboard/notifications")

        regulatory = (await self.db.execute(select(KnowledgeDocument).where(KnowledgeDocument.title.like("%Prototype 2026 Update%")).limit(1))).scalar_one_or_none()
        add("regulatory", "Regulatory update", bool(regulatory), "Versioned prototype knowledge-base change is available." if regulatory else "No seeded regulatory update found.", "/dashboard/regulatory")

        incentive = None
        if project:
            incentive = (await self.db.execute(select(IncentiveApplicationCase).where(IncentiveApplicationCase.project_id == project.id).limit(1))).scalar_one_or_none()
        add("incentive", "Incentive readiness", bool(incentive), "A prototype incentive preparation case is available." if incentive else "No seeded incentive case found.", f"/dashboard/{project.id}/schemes" if project else "/dashboard")

        gateway = GatewayService().catalog()
        prototype = gateway.get("provider") == "prototype"
        add("integration", "Government integration transparency", prototype, "Prototype simulator is active; no live government API is assumed." if prototype else "Demo requires the prototype provider.", "/dashboard/integrations")

        passed = sum(1 for c in checks if c["ok"])
        return {
            "ready": passed == len(checks),
            "score": round((passed / len(checks)) * 100, 1) if checks else 0,
            "passed": passed,
            "total": len(checks),
            "project_id": str(project.id) if project else None,
            "project_name": project.name if project else None,
            "query_application_id": query_approval.application_id if query_approval else None,
            "preparation_application_id": prep_approval.application_id if prep_approval else None,
            "checks": checks,
            "demo_mode": "si_demo",
            "integration_provider": gateway.get("provider"),
            "disclaimer": "SIH prototype readiness only. Seeded data and simulator responses are not live government records.",
        }
