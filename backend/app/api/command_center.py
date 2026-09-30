"""Unified project approval command center API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.core.database import get_db_session
from app.services.command_center import CommandCenterService

router = APIRouter(prefix="/command-center", tags=["command-center"])


@router.get("/projects/{project_id}")
async def get_project_command_center(
    project_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Return a single owner-scoped operational view for one project."""
    try:
        return await CommandCenterService(db).build(project_id, UUID(str(user["sub"])))
    except ValueError as exc:
        message = str(exc)
        lowered = message.lower()
        if "not owned" in lowered or "not authorized" in lowered:
            status_code = 403
        elif "not found" in lowered:
            status_code = 404
        else:
            status_code = 400
        raise HTTPException(status_code=status_code, detail=message) from exc
