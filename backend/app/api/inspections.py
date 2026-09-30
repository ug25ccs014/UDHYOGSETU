"""Inspection planning APIs for applicants and officers/admins."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.models import Project
from app.schemas import InspectionScheduleRequest, InspectionUpdateRequest
from app.services.inspection_planner import InspectionPlannerService

router = APIRouter(prefix="/inspections", tags=["inspections"])


def _is_officer(user: dict) -> bool:
    return (user.get("role") or "").upper() in {"OFFICER", "ADMIN"}


@router.get("/officers")
async def list_inspection_officers(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List active officers/admins available for inspection assignment."""
    if not _is_officer(user):
        raise HTTPException(status_code=403, detail="Officer or Admin access required")
    officers = await InspectionPlannerService(db).list_officers()
    return {
        "officers": [
            {"id": str(o.id), "name": o.name, "email": o.email}
            for o in officers
        ]
    }


@router.get("/coordination-suggestions")
async def coordination_suggestions(
    project_id: UUID | None = Query(default=None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Find pending inspections that may be coordinated into common site visits."""
    service = InspectionPlannerService(db)
    try:
        if project_id:
            await service.authorize_project_view(project_id, user)
            suggestions = await service.coordination_suggestions(project_id)
        elif _is_officer(user):
            suggestions = await service.coordination_suggestions()
        else:
            suggestions = await service.coordination_suggestions(owner_user_id=UUID(str(user["sub"])))
        return {"suggestions": suggestions}
    except ValueError as exc:
        status = 404 if "not found" in str(exc).lower() else 403
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.get("")
async def list_inspections(
    project_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    assigned_officer_id: UUID | None = Query(default=None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List inspection visits, owner-scoped for entrepreneurs and global for officers."""
    service = InspectionPlannerService(db)
    if not _is_officer(user) and project_id:
        try:
            await service.authorize_project_view(project_id, user)
        except ValueError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
    visits = await service.list_visits(
        project_id=project_id,
        status=status,
        assigned_officer_id=assigned_officer_id,
        owner_user_id=UUID(str(user["sub"])) if not _is_officer(user) and not project_id else None,
    )
    return {"inspections": [await service.serialize(v) for v in visits]}


@router.get("/application/{application_id}")
async def list_application_inspections(
    application_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List inspection visits linked to one application."""
    service = InspectionPlannerService(db)
    try:
        approval = await service.resolve_application(application_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    visits = await service.get_for_application(approval)
    if not visits:
        project_result = await db.execute(select(Project).where(Project.id == approval.project_id))
        project = project_result.scalar_one_or_none()
        if not _is_officer(user) and (not project or str(project.user_id) != str(user.get("sub"))):
            raise HTTPException(status_code=403, detail="Not authorized to access this application")
    else:
        try:
            await service.authorize_view(visits[0], user)
        except ValueError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"inspections": [await service.serialize(v) for v in visits]}


@router.get("/{inspection_id}")
async def get_inspection(
    inspection_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    service = InspectionPlannerService(db)
    try:
        visit = await service._get_visit(inspection_id)
        await service.authorize_view(visit, user)
    except ValueError as exc:
        status = 404 if "not found" in str(exc).lower() else 403
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    return await service.serialize(visit)


@router.post("/schedule")
async def schedule_inspection(
    payload: InspectionScheduleRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Schedule one or more approvals into a single inspection visit."""
    if not _is_officer(user):
        raise HTTPException(status_code=403, detail="Officer or Admin access required")
    service = InspectionPlannerService(db)
    try:
        visit = await service.schedule(
            approval_ids=payload.approval_ids,
            scheduled_start=payload.scheduled_start,
            scheduled_end=payload.scheduled_end,
            assigned_officer_id=payload.assigned_officer_id,
            location=payload.location,
            notes=payload.notes,
            actor_user_id=UUID(str(user["sub"])),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    from app.audit.logging import log_audit
    from app.notifications.service import NotificationService

    project = await service._get_project(visit.project_id)
    response_payload = await service.serialize(visit)
    try:
        await log_audit(
            db,
            user_id=str(user["sub"]),
            action="inspection.scheduled",
            resource_type="inspection_visit",
            resource_id=str(visit.id),
            details={
                "project_id": str(project.id),
                "approval_ids": [str(aid) for aid in payload.approval_ids],
                "scheduled_start": visit.scheduled_start.isoformat(),
                "scheduled_end": visit.scheduled_end.isoformat(),
                "coordinated": len(payload.approval_ids) > 1,
            },
        )
    except Exception:
        # Audit is valuable but should not make a valid scheduling action fail.
        await db.rollback()

    try:
        owner_id = project.user_id
        title = "Inspection Scheduled"
        message = (
            f"An inspection visit is scheduled for {project.name} on "
            f"{visit.scheduled_start.strftime('%d %b %Y, %H:%M')}"
        )
        if len(payload.approval_ids) > 1:
            message += f" covering {len(payload.approval_ids)} approval(s)."
        else:
            message += "."
        await NotificationService(db).create(
            str(owner_id),
            title,
            message,
            category="inspection",
            severity="info",
            project_id=project.id,
            reference_id=str(visit.id),
        )
    except Exception:
        await db.rollback()

    return response_payload


@router.patch("/{inspection_id}")
async def update_inspection(
    inspection_id: UUID,
    payload: InspectionUpdateRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Reschedule, reassign, cancel, or complete an inspection visit."""
    if not _is_officer(user):
        raise HTTPException(status_code=403, detail="Officer or Admin access required")
    service = InspectionPlannerService(db)
    try:
        visit = await service.update(
            inspection_id,
            scheduled_start=payload.scheduled_start,
            scheduled_end=payload.scheduled_end,
            assigned_officer_id=payload.assigned_officer_id,
            location=payload.location,
            notes=payload.notes,
            status=payload.status,
            checklist=payload.checklist,
        )
    except ValueError as exc:
        status = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc

    from app.audit.logging import log_audit
    response_payload = await service.serialize(visit)
    try:
        await log_audit(
            db,
            user_id=str(user["sub"]),
            action="inspection.updated",
            resource_type="inspection_visit",
            resource_id=str(visit.id),
            details={
                "status": visit.status,
                "scheduled_start": visit.scheduled_start.isoformat(),
                "scheduled_end": visit.scheduled_end.isoformat(),
                "assigned_officer_id": str(visit.assigned_officer_id) if visit.assigned_officer_id else None,
            },
        )
    except Exception:
        await db.rollback()

    try:
        project_result = await db.execute(select(Project).where(Project.id == visit.project_id))
        project = project_result.scalar_one_or_none()
        if project:
            from app.notifications.service import NotificationService
            await NotificationService(db).create(
                str(project.user_id),
                "Inspection Updated",
                f"The inspection visit for {project.name} was updated to {visit.status.lower().replace('_', ' ')}.",
                category="inspection",
                severity="info",
                project_id=project.id,
                reference_id=str(visit.id),
            )
    except Exception:
        await db.rollback()
    return response_payload
