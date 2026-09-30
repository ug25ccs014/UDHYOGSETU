"""Applicant grievance and escalation case-management APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_auth, require_officer
from app.core.database import get_db_session
from app.schemas import GrievanceCreateRequest, GrievanceEscalateRequest, GrievanceTransitionRequest
from app.services.grievance import GrievanceService

router = APIRouter(prefix="/grievances", tags=["grievances"])


def _is_officer(user: dict) -> bool:
    return str(user.get("role", "")).upper() in {"OFFICER", "ADMIN"}


@router.get("/officers")
async def list_grievance_officers(
    user: dict = Depends(require_officer),
    db: AsyncSession = Depends(get_db_session),
):
    """List active officers/admins that can be assigned a grievance."""
    from app.models import User, UserRole
    result = await db.execute(
        select(User).where(
            User.is_active.is_(True),
            User.role.in_([UserRole.OFFICER, UserRole.ADMIN]),
        ).order_by(User.name.asc())
    )
    return {"officers": [{"id": str(u.id), "name": u.name, "email": u.email} for u in result.scalars().all()]}


@router.get("")
async def list_grievances(
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
    assigned_officer_id: UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    service = GrievanceService(db)
    try:
        grievances = await service.list_for_user(
            user,
            status=status,
            priority=priority,
            project_id=project_id,
            assigned_officer_id=assigned_officer_id,
            limit=limit,
        )
        return {"grievances": [await service.serialize(g) for g in grievances]}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/summary")
async def grievance_summary(
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    return await GrievanceService(db).summary(user)


@router.post("")
async def create_grievance(
    payload: GrievanceCreateRequest,
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    service = GrievanceService(db)
    try:
        grievance = await service.create(
            UUID(str(user["sub"])),
            application_id=payload.application_id,
            project_id=payload.project_id,
            category=payload.category,
            subject=payload.subject,
            description=payload.description,
            priority=payload.priority,
        )
    except ValueError as exc:
        status_code = 403 if "authorized" in str(exc).lower() else 400
        if "not found" in str(exc).lower():
            status_code = 404
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    await _safe_audit(db, user, "grievance.created", grievance, {"priority": grievance.priority})
    await _safe_owner_notification(
        db,
        user_id=str(user["sub"]),
        title="Grievance Submitted",
        message=f"Your grievance '{grievance.subject}' has been recorded in UDYOGSETU.",
        project_id=grievance.project_id,
        reference_id=str(grievance.id),
        severity="info",
    )
    return await service.serialize(grievance)


@router.get("/{grievance_id}")
async def get_grievance(
    grievance_id: UUID,
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    service = GrievanceService(db)
    try:
        grievance = await service.get(grievance_id)
        await service.authorize_view(grievance, user)
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 403
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return await service.serialize(grievance)


@router.post("/{grievance_id}/transition")
async def transition_grievance(
    grievance_id: UUID,
    payload: GrievanceTransitionRequest,
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    service = GrievanceService(db)
    try:
        grievance = await service.transition(
            grievance_id,
            actor_user_id=UUID(str(user["sub"])),
            actor_role=str(user.get("role", "ENTREPRENEUR")),
            to_status=payload.to_status,
            note=payload.note,
            assigned_officer_id=payload.assigned_officer_id,
            resolution_note=payload.resolution_note,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else (403 if "authorized" in message.lower() else 400)
        raise HTTPException(status_code=status_code, detail=message) from exc
    await _safe_audit(db, user, "grievance.status_changed", grievance, {"to_status": grievance.status})
    await _notify_grievance_update(db, grievance, "Grievance Updated", f"Your grievance '{grievance.subject}' is now {grievance.status.lower().replace('_', ' ')}.")
    return await service.serialize(grievance)


@router.post("/{grievance_id}/escalate")
async def escalate_grievance(
    grievance_id: UUID,
    payload: GrievanceEscalateRequest,
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    service = GrievanceService(db)
    try:
        grievance = await service.request_escalation(
            grievance_id,
            UUID(str(user["sub"])),
            str(user.get("role", "ENTREPRENEUR")),
            payload.reason,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else (403 if "authorized" in message.lower() else 400)
        raise HTTPException(status_code=status_code, detail=message) from exc
    await _safe_audit(db, user, "grievance.escalated", grievance, {"level": grievance.escalation_level, "reason": grievance.escalation_reason})
    await _notify_grievance_update(db, grievance, "Grievance Escalated", f"Grievance '{grievance.subject}' was escalated to level {grievance.escalation_level}.")
    return await service.serialize(grievance)


async def _safe_audit(db: AsyncSession, user: dict, action: str, grievance, details: dict):
    try:
        from app.audit.logging import log_audit
        await log_audit(db, str(user["sub"]), action, "grievance", str(grievance.id), details=details)
    except Exception:
        await db.rollback()


async def _safe_owner_notification(db: AsyncSession, *, user_id: str, title: str, message: str, project_id, reference_id: str, severity: str):
    try:
        from app.notifications.service import NotificationService
        await NotificationService(db).create(user_id, title, message, category="grievance", severity=severity, project_id=project_id, reference_id=reference_id)
    except Exception:
        await db.rollback()


async def _notify_grievance_update(db: AsyncSession, grievance, title: str, message: str):
    try:
        from app.notifications.service import NotificationService
        await NotificationService(db).create(
            str(grievance.user_id), title, message, category="grievance", severity="warning" if grievance.status == "ESCALATED" else "info",
            project_id=grievance.project_id, reference_id=str(grievance.id),
        )
    except Exception:
        await db.rollback()
