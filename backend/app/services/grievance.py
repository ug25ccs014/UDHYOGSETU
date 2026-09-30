"""Grievance and escalation workflow for UDYOGSETU.

This module records applicant complaints/escalations locally. It is an
operational case-management layer and does not claim to transmit grievances to
or act on behalf of a government authority.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Approval, Grievance, GrievanceEvent, Project, User, UserRole
from app.services.sla_risk import SlaRiskService

_ACTIVE_STATUSES = {"OPEN", "ACKNOWLEDGED", "IN_REVIEW", "ESCALATED"}
_TERMINAL_STATUSES = {"RESOLVED", "CLOSED", "REJECTED"}
_ALLOWED_STATUSES = _ACTIVE_STATUSES | _TERMINAL_STATUSES
_PRIORITY_TARGET_DAYS = {"HIGH": 3, "MEDIUM": 7, "LOW": 15}

_STATUS_TRANSITIONS = {
    "OPEN": {"ACKNOWLEDGED", "IN_REVIEW", "ESCALATED", "RESOLVED", "REJECTED"},
    "ACKNOWLEDGED": {"IN_REVIEW", "ESCALATED", "RESOLVED", "REJECTED"},
    "IN_REVIEW": {"ACKNOWLEDGED", "ESCALATED", "RESOLVED", "REJECTED"},
    "ESCALATED": {"IN_REVIEW", "RESOLVED", "REJECTED"},
    "RESOLVED": {"CLOSED"},
    "CLOSED": set(),
    "REJECTED": set(),
}


def _status(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _priority(value: str | None) -> str:
    normalized = (value or "MEDIUM").upper()
    if normalized not in _PRIORITY_TARGET_DAYS:
        raise ValueError("Priority must be LOW, MEDIUM, or HIGH")
    return normalized


class GrievanceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve_application(self, application_id: str) -> Approval:
        result = await self.db.execute(
            select(Approval).where(Approval.application_id == application_id)
        )
        approval = result.scalar_one_or_none()
        if not approval:
            try:
                result = await self.db.execute(select(Approval).where(Approval.id == UUID(application_id)))
                approval = result.scalar_one_or_none()
            except (ValueError, TypeError, AttributeError):
                approval = None
        if not approval:
            raise ValueError("Application not found")
        return approval

    async def _project(self, project_id: UUID) -> Project:
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")
        return project

    async def get(self, grievance_id: UUID) -> Grievance:
        result = await self.db.execute(select(Grievance).where(Grievance.id == grievance_id))
        grievance = result.scalar_one_or_none()
        if not grievance:
            raise ValueError("Grievance not found")
        return grievance

    async def authorize_view(self, grievance: Grievance, user: dict) -> None:
        role = str(user.get("role", "")).upper()
        if role in {"OFFICER", "ADMIN"}:
            return
        if str(grievance.user_id) != str(user.get("sub")):
            raise ValueError("Not authorized to access this grievance")

    async def list_for_user(
        self,
        user: dict,
        *,
        status: str | None = None,
        priority: str | None = None,
        project_id: UUID | None = None,
        assigned_officer_id: UUID | None = None,
        limit: int = 100,
    ) -> list[Grievance]:
        stmt = select(Grievance).order_by(desc(Grievance.updated_at), desc(Grievance.created_at))
        role = str(user.get("role", "")).upper()
        if role not in {"OFFICER", "ADMIN"}:
            stmt = stmt.where(Grievance.user_id == UUID(str(user["sub"])))
        if project_id:
            stmt = stmt.where(Grievance.project_id == project_id)
        if assigned_officer_id and role in {"OFFICER", "ADMIN"}:
            stmt = stmt.where(Grievance.assigned_officer_id == assigned_officer_id)
        if status:
            normalized = status.upper()
            if normalized not in _ALLOWED_STATUSES:
                raise ValueError(f"Unknown grievance status: {status}")
            stmt = stmt.where(Grievance.status == normalized)
        if priority:
            stmt = stmt.where(Grievance.priority == _priority(priority))
        stmt = stmt.limit(max(1, min(limit, 200)))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        user_id: UUID,
        *,
        application_id: str | None,
        project_id: UUID | None,
        category: str,
        subject: str,
        description: str,
        priority: str,
    ) -> Grievance:
        if not subject.strip() or not description.strip():
            raise ValueError("Subject and description are required")
        approval = None
        if application_id:
            approval = await self.resolve_application(application_id)
            if project_id and approval.project_id != project_id:
                raise ValueError("Application does not belong to the selected project")
            project_id = approval.project_id
        if not project_id:
            raise ValueError("project_id or application_id is required")
        project = await self._project(project_id)
        if project.user_id != user_id:
            raise ValueError("Not authorized to create a grievance for this project")

        priority_value = _priority(priority)
        now = datetime.utcnow()
        target = now + timedelta(days=_PRIORITY_TARGET_DAYS[priority_value])
        grievance = Grievance(
            user_id=user_id,
            project_id=project_id,
            approval_id=approval.id if approval else None,
            application_id=application_id or (approval.application_id if approval else None),
            department=approval.department if approval else None,
            category=category.strip() or "Other",
            subject=subject.strip(),
            description=description.strip(),
            priority=priority_value,
            status="OPEN",
            escalation_level=0,
            response_target_at=target,
        )
        self.db.add(grievance)
        await self.db.flush()
        await self._event(
            grievance,
            actor_id=user_id,
            event_type="CREATED",
            from_status=None,
            to_status="OPEN",
            note="Grievance submitted by applicant.",
        )
        await self.db.commit()
        await self.db.refresh(grievance)
        return grievance

    async def transition(
        self,
        grievance_id: UUID,
        *,
        actor_user_id: UUID,
        actor_role: str,
        to_status: str,
        note: str | None = None,
        assigned_officer_id: UUID | None = None,
        resolution_note: str | None = None,
    ) -> Grievance:
        grievance = await self.get(grievance_id)
        role = actor_role.upper()
        current = _status(grievance.status)
        target = to_status.upper()
        if target not in _ALLOWED_STATUSES:
            raise ValueError(f"Unknown grievance status: {to_status}")
        assignment_only = target == current and assigned_officer_id is not None
        if target == current and not assignment_only:
            raise ValueError("Grievance is already in that status")

        if role not in {"OFFICER", "ADMIN"}:
            if str(grievance.user_id) != str(actor_user_id):
                raise ValueError("Not authorized to update this grievance")
            allowed_for_applicant = {"CLOSED"} if current == "RESOLVED" else {"ESCALATED"}
            if target not in allowed_for_applicant:
                raise ValueError("Applicants can close a resolved grievance; department actions require officer access")
        else:
            if target not in _STATUS_TRANSITIONS.get(current, set()):
                raise ValueError(f"Cannot move grievance from {current} to {target}")

        if assigned_officer_id is not None:
            officer_result = await self.db.execute(
                select(User).where(
                    User.id == assigned_officer_id,
                    User.is_active.is_(True),
                    User.role.in_([UserRole.OFFICER, UserRole.ADMIN]),
                )
            )
            if not officer_result.scalar_one_or_none():
                raise ValueError("Assigned officer was not found or is inactive")
            grievance.assigned_officer_id = assigned_officer_id

        if target == "ESCALATED":
            grievance.escalation_level = min(2, max(1, grievance.escalation_level + 1))
            grievance.escalated_at = datetime.utcnow()
            grievance.escalation_reason = (note or grievance.escalation_reason or "Escalation requested for unresolved case.").strip()
        if target == "RESOLVED":
            if not resolution_note and not note:
                raise ValueError("A resolution note is required to resolve a grievance")
            grievance.resolution_note = (resolution_note or note).strip()
            grievance.resolved_at = datetime.utcnow()
        if target == "CLOSED":
            if current != "RESOLVED":
                raise ValueError("Only resolved grievances can be closed")
            grievance.closed_at = datetime.utcnow()
        if target == "REJECTED":
            grievance.resolution_note = (resolution_note or note or "Case rejected by authorized officer.").strip()
            grievance.resolved_at = datetime.utcnow()

        grievance.status = target
        await self._event(
            grievance,
            actor_id=actor_user_id,
            event_type="ASSIGNED" if assignment_only else "STATUS_CHANGED",
            from_status=current,
            to_status=target,
            note=note or resolution_note or (f"Assigned to officer {grievance.assigned_officer_id}" if assignment_only else None),
        )
        await self.db.commit()
        await self.db.refresh(grievance)
        return grievance

    async def request_escalation(self, grievance_id: UUID, actor_user_id: UUID, actor_role: str, reason: str) -> Grievance:
        grievance = await self.get(grievance_id)
        role = actor_role.upper()
        if role not in {"OFFICER", "ADMIN"} and str(grievance.user_id) != str(actor_user_id):
            raise ValueError("Not authorized to escalate this grievance")
        if grievance.status in _TERMINAL_STATUSES:
            raise ValueError("A resolved, closed, or rejected grievance cannot be escalated")
        if not reason.strip():
            raise ValueError("Escalation reason is required")
        if grievance.escalation_level >= 2:
            raise ValueError("Maximum escalation level reached")

        # A second escalation keeps the case in ESCALATED but advances the
        # operational escalation level (for example, department desk -> senior
        # officer). Keep this separate from a normal status transition because
        # ESCALATED -> ESCALATED is intentionally not a state change.
        if grievance.status == "ESCALATED":
            if role not in {"OFFICER", "ADMIN"}:
                raise ValueError("A grievance already escalated must be handled by an authorized officer")
            previous_level = grievance.escalation_level
            grievance.escalation_level = min(2, grievance.escalation_level + 1)
            grievance.escalated_at = datetime.utcnow()
            grievance.escalation_reason = reason.strip()
            await self._event(
                grievance,
                actor_id=actor_user_id,
                event_type="ESCALATION_LEVEL_CHANGED",
                from_status="ESCALATED",
                to_status="ESCALATED",
                note=f"Escalation level {previous_level} -> {grievance.escalation_level}: {reason.strip()}",
            )
            await self.db.commit()
            await self.db.refresh(grievance)
            return grievance

        return await self.transition(
            grievance_id,
            actor_user_id=actor_user_id,
            actor_role=role,
            to_status="ESCALATED",
            note=reason.strip(),
        )

    async def serialize(self, grievance: Grievance) -> dict:
        project = await self._project(grievance.project_id)
        assigned_name = None
        if grievance.assigned_officer_id:
            result = await self.db.execute(select(User).where(User.id == grievance.assigned_officer_id))
            officer = result.scalar_one_or_none()
            assigned_name = officer.name if officer else None

        events_result = await self.db.execute(
            select(GrievanceEvent, User.name)
            .join(User, User.id == GrievanceEvent.actor_user_id)
            .where(GrievanceEvent.grievance_id == grievance.id)
            .order_by(GrievanceEvent.created_at.asc())
        )
        events = [
            {
                "id": str(event.id),
                "event_type": event.event_type,
                "from_status": event.from_status,
                "to_status": event.to_status,
                "note": event.note,
                "actor_name": actor_name,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event, actor_name in events_result.all()
        ]

        now = datetime.utcnow()
        days_to_target = (grievance.response_target_at - now).total_seconds() / 86400 if grievance.response_target_at else None
        sla_context = None
        if grievance.approval_id:
            try:
                approval = (await self.db.execute(select(Approval).where(Approval.id == grievance.approval_id))).scalar_one_or_none()
                if approval:
                    sla_context = (await SlaRiskService(self.db).evaluate_approval(approval, project))
            except Exception:  # noqa: BLE001 - grievance view must remain available if risk enrichment fails
                sla_context = None
        return {
            "id": str(grievance.id),
            "project_id": str(grievance.project_id),
            "project_name": project.name,
            "company_name": project.company_name,
            "approval_id": str(grievance.approval_id) if grievance.approval_id else None,
            "application_id": grievance.application_id,
            "department": grievance.department,
            "category": grievance.category,
            "subject": grievance.subject,
            "description": grievance.description,
            "priority": grievance.priority,
            "status": grievance.status,
            "escalation_level": grievance.escalation_level,
            "escalation_reason": grievance.escalation_reason,
            "assigned_officer_id": str(grievance.assigned_officer_id) if grievance.assigned_officer_id else None,
            "assigned_officer_name": assigned_name,
            "response_target_at": grievance.response_target_at.isoformat() if grievance.response_target_at else None,
            "days_to_response_target": round(days_to_target, 1) if days_to_target is not None else None,
            "escalated_at": grievance.escalated_at.isoformat() if grievance.escalated_at else None,
            "resolved_at": grievance.resolved_at.isoformat() if grievance.resolved_at else None,
            "closed_at": grievance.closed_at.isoformat() if grievance.closed_at else None,
            "resolution_note": grievance.resolution_note,
            "created_at": grievance.created_at.isoformat() if grievance.created_at else None,
            "updated_at": grievance.updated_at.isoformat() if grievance.updated_at else None,
            "events": events,
            "sla_context": sla_context,
            "disclaimer": "Grievances are recorded and managed in UDYOGSETU. External authority escalation/transmission requires an authorized integration and is not performed by this prototype.",
        }

    async def summary(self, user: dict) -> dict:
        grievances = await self.list_for_user(user, limit=200)
        status_counts = Counter(_status(g.status) for g in grievances)
        priority_counts = Counter(g.priority for g in grievances)
        overdue = sum(
            1
            for g in grievances
            if g.response_target_at and g.response_target_at < datetime.utcnow() and _status(g.status) in _ACTIVE_STATUSES
        )
        return {
            "total": len(grievances),
            "open": sum(status_counts.get(s, 0) for s in _ACTIVE_STATUSES),
            "escalated": status_counts.get("ESCALATED", 0),
            "resolved": status_counts.get("RESOLVED", 0),
            "closed": status_counts.get("CLOSED", 0),
            "overdue_targets": overdue,
            "by_status": dict(status_counts),
            "by_priority": dict(priority_counts),
        }

    async def _event(
        self,
        grievance: Grievance,
        *,
        actor_id: UUID,
        event_type: str,
        from_status: str | None,
        to_status: str | None,
        note: str | None,
    ) -> None:
        self.db.add(
            GrievanceEvent(
                grievance_id=grievance.id,
                actor_user_id=actor_id,
                event_type=event_type,
                from_status=from_status,
                to_status=to_status,
                note=note,
            )
        )
