from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.models import Approval, Document, Project
from app.services.project import ProjectService


async def _ensure_owner(db: AsyncSession, user: dict, project_id: UUID, not_found: str = "Project not found") -> Project:
    """Fetch a project and verify the authenticated user owns it (404/403 otherwise)."""
    service = ProjectService(db)
    project = await service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=not_found)
    if str(project.user_id) != str(user["sub"]):
        raise HTTPException(status_code=403, detail="Not authorized to access this project")
    return project


async def get_owned_project(
    project_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Project:
    """Dependency: current user must own the project."""
    return await _ensure_owner(db, user, project_id)


async def get_owned_approval(
    approval_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Approval:
    """Dependency: current user must own the project an approval belongs to."""
    result = await db.execute(select(Approval).where(Approval.id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    await _ensure_owner(db, user, approval.project_id)
    return approval


async def get_owned_document(
    document_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Document:
    """Dependency: current user must own the project a document belongs to."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    await _ensure_owner(db, user, document.project_id)
    return document


async def require_project_owner(
    project_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Dependency for endpoints that already look up project-scoped data."""
    await _ensure_owner(db, user, project_id)


async def require_auth(
    user: dict = Depends(get_current_user),
) -> dict:
    """Dependency: any authenticated user (no resource scoping needed)."""
    return user


_OFFICER_ROLES = {"OFFICER", "ADMIN"}


async def require_officer(user: dict = Depends(get_current_user)) -> dict:
    """Dependency: authenticated user must hold the OFFICER or ADMIN role."""
    role = (user.get("role") or "").upper()
    if role not in _OFFICER_ROLES:
        raise HTTPException(status_code=403, detail="Officer or Admin access required")
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Dependency: authenticated user must hold the ADMIN role."""
    role = (user.get("role") or "").upper()
    if role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user