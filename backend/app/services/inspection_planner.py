"""Inspection planning and common site-visit coordination.

This service coordinates the operational scheduling of inspections without
making or predicting statutory decisions. A single ``InspectionVisit`` can
cover multiple approvals for the same project, which lets departments plan a
common site visit when operationally appropriate.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Approval,
    ApprovalStatus,
    InspectionVisit,
    InspectionVisitStatus,
    Project,
    User,
    UserRole,
    inspection_visit_approvals,
)

_ACTIVE_STATUSES = {
    InspectionVisitStatus.SCHEDULED.value,
}
_INSPECTION_ELIGIBLE = {
    ApprovalStatus.UNDER_REVIEW,
    ApprovalStatus.INSPECTION,
}
_ALLOWED_STATUSES = {status.value for status in InspectionVisitStatus}
_DEFAULT_CHECKLIST = [
    {"id": "site-access", "label": "Site access and inspection area confirmed", "completed": False},
    {"id": "identity-docs", "label": "Company/project identity documents available", "completed": False},
    {"id": "site-safety", "label": "Site safety and PPE requirements reviewed", "completed": False},
]


def _utc_naive(value: datetime) -> datetime:
    """Normalize aware datetimes to naive UTC for existing DB conventions."""
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _display_location(project: Project) -> str:
    parts = [
        project.location_industrial_area,
        project.location_midc_estate,
        project.location_city,
        project.location_district,
        project.location_state,
    ]
    return ", ".join(dict.fromkeys(p.strip() for p in parts if isinstance(p, str) and p.strip()))


def _approval_application_id(approval: Approval) -> str:
    return approval.application_id or str(approval.id)


def _approval_checklist_items(approval: Approval) -> list[dict]:
    name = (approval.name or "").lower()
    items = []
    if "fire" in name:
        items.extend([
            {"id": "fire-extinguishers", "label": "Fire extinguishers / suppression systems accessible", "completed": False},
            {"id": "fire-plan", "label": "Fire safety plan and evacuation routes available", "completed": False},
        ])
    if "factory" in name or "industrial safety" in name:
        items.extend([
            {"id": "safety-equipment", "label": "Workplace safety equipment and controls visible", "completed": False},
            {"id": "worker-safety", "label": "Worker safety arrangements documented", "completed": False},
        ])
    if "boiler" in name:
        items.extend([
            {"id": "boiler-access", "label": "Boiler and safety-valve access available", "completed": False},
            {"id": "boiler-records", "label": "Boiler maintenance/test records available", "completed": False},
        ])
    if "mpcb" in name or "pollution" in name:
        items.extend([
            {"id": "etp-access", "label": "ETP / pollution-control equipment accessible", "completed": False},
            {"id": "environment-records", "label": "Environmental monitoring records available", "completed": False},
        ])
    return items


class InspectionPlannerService:
    """Owns inspection scheduling, coordination suggestions and visit lifecycle."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_officers(self) -> list[User]:
        result = await self.db.execute(
            select(User)
            .where(User.role.in_([UserRole.OFFICER, UserRole.ADMIN]), User.is_active.is_(True))
            .order_by(User.name.asc())
        )
        return list(result.scalars().all())

    async def _get_project(self, project_id: UUID) -> Project:
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")
        return project

    async def resolve_application(self, application_id: str) -> Approval:
        """Resolve an approval by government-style application ID or internal UUID."""
        result = await self.db.execute(
            select(Approval).where(Approval.application_id == application_id)
        )
        approval = result.scalar_one_or_none()
        if approval:
            return approval
        try:
            approval_uuid = UUID(str(application_id))
        except (ValueError, AttributeError, TypeError):
            approval_uuid = None
        if approval_uuid:
            result = await self.db.execute(select(Approval).where(Approval.id == approval_uuid))
            approval = result.scalar_one_or_none()
        if not approval:
            raise ValueError("Application not found")
        return approval

    async def _get_approvals(self, approval_ids: Iterable[UUID]) -> list[Approval]:
        ids = list(dict.fromkeys(approval_ids))
        if not ids:
            raise ValueError("At least one approval is required")
        result = await self.db.execute(select(Approval).where(Approval.id.in_(ids)))
        approvals = list(result.scalars().all())
        if len(approvals) != len(ids):
            raise ValueError("One or more approvals were not found")
        return approvals

    async def _get_visit(self, visit_id: UUID) -> InspectionVisit:
        result = await self.db.execute(select(InspectionVisit).where(InspectionVisit.id == visit_id))
        visit = result.scalar_one_or_none()
        if not visit:
            raise ValueError("Inspection visit not found")
        return visit

    async def _active_visit_for_approval(self, approval_id: UUID) -> InspectionVisit | None:
        result = await self.db.execute(
            select(InspectionVisit)
            .join(
                inspection_visit_approvals,
                inspection_visit_approvals.c.inspection_visit_id == InspectionVisit.id,
            )
            .where(
                inspection_visit_approvals.c.approval_id == approval_id,
                InspectionVisit.status.in_(_ACTIVE_STATUSES),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _check_officer_conflict(
        self,
        officer_id: UUID | None,
        start: datetime,
        end: datetime,
        exclude_visit_id: UUID | None = None,
    ) -> None:
        if not officer_id:
            return
        stmt = select(InspectionVisit).where(
            InspectionVisit.assigned_officer_id == officer_id,
            InspectionVisit.status.in_(_ACTIVE_STATUSES),
            InspectionVisit.scheduled_start < end,
            InspectionVisit.scheduled_end > start,
        )
        if exclude_visit_id:
            stmt = stmt.where(InspectionVisit.id != exclude_visit_id)
        result = await self.db.execute(stmt)
        conflict = result.scalar_one_or_none()
        if conflict:
            raise ValueError(
                "Assigned officer has another inspection during the selected time window"
            )

    async def _make_checklist(self, approvals: list[Approval]) -> list[dict]:
        items = list(_DEFAULT_CHECKLIST)
        seen = {i["id"] for i in items}
        for approval in approvals:
            for item in _approval_checklist_items(approval):
                if item["id"] not in seen:
                    items.append(item)
                    seen.add(item["id"])
        return items

    async def schedule(
        self,
        approval_ids: list[UUID],
        scheduled_start: datetime,
        scheduled_end: datetime,
        assigned_officer_id: UUID | None,
        location: str | None,
        notes: str | None,
        actor_user_id: UUID,
    ) -> InspectionVisit:
        start = _utc_naive(scheduled_start)
        end = _utc_naive(scheduled_end)
        if end <= start:
            raise ValueError("scheduled_end must be after scheduled_start")
        if end - start > timedelta(hours=12):
            raise ValueError("Inspection visit cannot exceed 12 hours")

        approvals = await self._get_approvals(approval_ids)
        project_ids = {a.project_id for a in approvals}
        if len(project_ids) != 1:
            raise ValueError("A common inspection visit can only coordinate approvals from one project")
        for approval in approvals:
            if approval.status not in _INSPECTION_ELIGIBLE:
                raise ValueError(
                    f"{approval.name} is {getattr(approval.status, 'value', approval.status)}; "
                    "only Under Review or Inspection applications can be scheduled"
                )
            existing = await self._active_visit_for_approval(approval.id)
            if existing:
                raise ValueError(f"{approval.name} already has an active inspection visit")

        officer_id = assigned_officer_id or actor_user_id
        officer_result = await self.db.execute(
            select(User).where(
                User.id == officer_id,
                User.is_active.is_(True),
                User.role.in_([UserRole.OFFICER, UserRole.ADMIN]),
            )
        )
        officer = officer_result.scalar_one_or_none()
        if not officer:
            raise ValueError("Assigned officer was not found or is not active")
        await self._check_officer_conflict(officer.id, start, end)

        project = await self._get_project(next(iter(project_ids)))
        resolved_location = (location or _display_location(project)).strip() or None
        coordinated = len(approvals) > 1
        visit = InspectionVisit(
            project_id=project.id,
            assigned_officer_id=officer.id,
            scheduled_start=start,
            scheduled_end=end,
            status=InspectionVisitStatus.SCHEDULED.value,
            location=resolved_location,
            notes=notes.strip() if isinstance(notes, str) else notes,
            checklist=await self._make_checklist(approvals),
            coordination_note=(
                f"Coordinated site visit for {len(approvals)} approvals; "
                f"{len(approvals) - 1} separate site visit(s) may be avoided by this plan."
                if coordinated
                else "Single-approval inspection visit."
            ),
        )
        self.db.add(visit)
        await self.db.flush()

        # Move eligible applications into INSPECTION using the existing governed workflow.
        from app.services.approval_workflow import ApprovalWorkflowEngine

        engine = ApprovalWorkflowEngine("OFFICER")
        for approval in approvals:
            if approval.status == ApprovalStatus.UNDER_REVIEW:
                decision = engine.apply(approval, ApprovalStatus.INSPECTION)
                if not decision.allowed:
                    raise ValueError(decision.error or f"Cannot move {approval.name} into inspection")
            await self.db.execute(
                inspection_visit_approvals.insert().values(
                    inspection_visit_id=visit.id,
                    approval_id=approval.id,
                )
            )
        await self.db.commit()
        await self.db.refresh(visit)
        return visit

    async def update(
        self,
        visit_id: UUID,
        *,
        scheduled_start: datetime | None = None,
        scheduled_end: datetime | None = None,
        assigned_officer_id: UUID | None = None,
        location: str | None = None,
        notes: str | None = None,
        status: str | None = None,
        checklist: list[dict] | None = None,
    ) -> InspectionVisit:
        visit = await self._get_visit(visit_id)
        if visit.status == InspectionVisitStatus.CANCELLED.value and status != InspectionVisitStatus.SCHEDULED.value:
            raise ValueError("Cancelled inspection visits cannot be edited")

        start = _utc_naive(scheduled_start) if scheduled_start else visit.scheduled_start
        end = _utc_naive(scheduled_end) if scheduled_end else visit.scheduled_end
        if end <= start:
            raise ValueError("scheduled_end must be after scheduled_start")

        if assigned_officer_id is not None:
            officer_result = await self.db.execute(
                select(User).where(
                    User.id == assigned_officer_id,
                    User.is_active.is_(True),
                    User.role.in_([UserRole.OFFICER, UserRole.ADMIN]),
                )
            )
            if not officer_result.scalar_one_or_none():
                raise ValueError("Assigned officer was not found or is not active")
        else:
            assigned_officer_id = visit.assigned_officer_id
        await self._check_officer_conflict(assigned_officer_id, start, end, exclude_visit_id=visit.id)

        if status:
            normalized_status = status.upper()
            if normalized_status not in _ALLOWED_STATUSES:
                raise ValueError(f"Unknown inspection status: {status}")
            if visit.status == InspectionVisitStatus.COMPLETED.value and normalized_status not in {InspectionVisitStatus.COMPLETED.value}:
                raise ValueError("Completed inspection visits cannot be reopened")
            visit.status = normalized_status
        visit.scheduled_start = start
        visit.scheduled_end = end
        visit.assigned_officer_id = assigned_officer_id
        if location is not None:
            visit.location = location.strip() or None
        if notes is not None:
            visit.notes = notes.strip() or None
        if checklist is not None:
            normalized = []
            for item in checklist:
                if not isinstance(item, dict) or not item.get("id") or not item.get("label"):
                    raise ValueError("Each checklist item must contain id and label")
                normalized.append({
                    "id": str(item["id"]),
                    "label": str(item["label"]),
                    "completed": bool(item.get("completed", False)),
                })
            visit.checklist = normalized
        await self.db.commit()
        await self.db.refresh(visit)
        return visit

    async def get_for_application(self, approval: Approval) -> list[InspectionVisit]:
        result = await self.db.execute(
            select(InspectionVisit)
            .join(
                inspection_visit_approvals,
                inspection_visit_approvals.c.inspection_visit_id == InspectionVisit.id,
            )
            .where(inspection_visit_approvals.c.approval_id == approval.id)
            .order_by(InspectionVisit.scheduled_start.desc())
        )
        return list(result.scalars().all())

    async def list_visits(
        self,
        *,
        project_id: UUID | None = None,
        status: str | None = None,
        assigned_officer_id: UUID | None = None,
        owner_user_id: UUID | None = None,
    ) -> list[InspectionVisit]:
        stmt = select(InspectionVisit).order_by(InspectionVisit.scheduled_start.asc())
        if project_id:
            stmt = stmt.where(InspectionVisit.project_id == project_id)
        if owner_user_id:
            stmt = stmt.join(Project, Project.id == InspectionVisit.project_id).where(Project.user_id == owner_user_id)
        if status:
            stmt = stmt.where(InspectionVisit.status == status.upper())
        if assigned_officer_id:
            stmt = stmt.where(InspectionVisit.assigned_officer_id == assigned_officer_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def coordination_suggestions(
        self,
        project_id: UUID | None = None,
        owner_user_id: UUID | None = None,
    ) -> list[dict]:
        stmt = select(Approval).where(Approval.status.in_(_INSPECTION_ELIGIBLE)).order_by(Approval.project_id, Approval.name)
        if project_id:
            stmt = stmt.where(Approval.project_id == project_id)
        if owner_user_id:
            stmt = stmt.join(Project, Project.id == Approval.project_id).where(Project.user_id == owner_user_id)
        result = await self.db.execute(stmt)
        approvals = list(result.scalars().all())

        candidates: list[Approval] = []
        for approval in approvals:
            if not await self._active_visit_for_approval(approval.id):
                candidates.append(approval)

        grouped: dict[UUID, list[Approval]] = defaultdict(list)
        for approval in candidates:
            grouped[approval.project_id].append(approval)

        suggestions = []
        for pid, items in grouped.items():
            if len(items) < 2:
                continue
            project = await self._get_project(pid)
            location = _display_location(project)
            applications = [
                {
                    "id": str(a.id),
                    "application_id": _approval_application_id(a),
                    "name": a.name,
                    "department": a.department,
                    "status": a.status.value if hasattr(a.status, "value") else str(a.status),
                    "risk_level": a.risk_level,
                    "estimated_processing_days": a.estimated_processing_days,
                }
                for a in items
            ]
            suggestions.append({
                "project_id": str(pid),
                "project_name": project.name,
                "company_name": project.company_name,
                "location": location,
                "approval_ids": [str(a.id) for a in items],
                "applications": applications,
                "approval_count": len(items),
                "separate_site_visits": len(items),
                "coordinated_site_visits": 1,
                "site_visits_avoided": len(items) - 1,
                "reason": "Same project and inspection location; these pending inspections may be coordinated operationally into one site visit.",
                "note": "Suggestion only. Statutory inspection requirements and independent departmental decisions remain unchanged.",
            })
        return suggestions

    async def serialize(self, visit: InspectionVisit) -> dict:
        project_result = await self.db.execute(select(Project).where(Project.id == visit.project_id))
        project = project_result.scalar_one_or_none()
        officer = None
        if visit.assigned_officer_id:
            officer_result = await self.db.execute(select(User).where(User.id == visit.assigned_officer_id))
            officer = officer_result.scalar_one_or_none()

        approval_result = await self.db.execute(
            select(Approval)
            .join(
                inspection_visit_approvals,
                inspection_visit_approvals.c.approval_id == Approval.id,
            )
            .where(inspection_visit_approvals.c.inspection_visit_id == visit.id)
            .order_by(Approval.name.asc())
        )
        approvals = list(approval_result.scalars().all())
        return {
            "id": str(visit.id),
            "project_id": str(visit.project_id),
            "project_name": project.name if project else None,
            "company_name": project.company_name if project else None,
            "assigned_officer_id": str(visit.assigned_officer_id) if visit.assigned_officer_id else None,
            "assigned_officer_name": officer.name if officer else None,
            "assigned_officer_email": officer.email if officer else None,
            "scheduled_start": visit.scheduled_start.isoformat(),
            "scheduled_end": visit.scheduled_end.isoformat(),
            "status": visit.status,
            "location": visit.location,
            "notes": visit.notes,
            "coordination_note": visit.coordination_note,
            "coordinated": len(approvals) > 1,
            "approvals": [
                {
                    "id": str(a.id),
                    "application_id": _approval_application_id(a),
                    "name": a.name,
                    "department": a.department,
                    "status": a.status.value if hasattr(a.status, "value") else str(a.status),
                    "risk_level": a.risk_level,
                    "estimated_processing_days": a.estimated_processing_days,
                }
                for a in approvals
            ],
            "checklist": visit.checklist or [],
            "created_at": visit.created_at.isoformat() if visit.created_at else None,
            "updated_at": visit.updated_at.isoformat() if visit.updated_at else None,
        }

    async def authorize_view(self, visit: InspectionVisit, user: dict) -> None:
        if (user.get("role") or "").upper() in {"OFFICER", "ADMIN"}:
            return
        result = await self.db.execute(select(Project).where(Project.id == visit.project_id))
        project = result.scalar_one_or_none()
        if not project or str(project.user_id) != str(user.get("sub")):
            raise ValueError("Not authorized to access this inspection")

    async def authorize_project_view(self, project_id: UUID, user: dict) -> None:
        if (user.get("role") or "").upper() in {"OFFICER", "ADMIN"}:
            return
        project = await self._get_project(project_id)
        if str(project.user_id) != str(user.get("sub")):
            raise ValueError("Not authorized to access this project")
