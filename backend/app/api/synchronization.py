"""Synchronization + query-resolution API — spec §19, §20.

  * POST /synchronization/sync            -> poll all tracked gov applications
  * POST /synchronization/{approval_id}/track -> link an approval to a gov system
  * GET  /synchronization/{approval_id}/query-resolution -> AI explain a gov query
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_officer
from app.core.database import get_db_session
from app.core.security import get_current_user
from app.models import Approval, Project
from app.services.gov_sync_service import GovSyncService
from app.services.query_resolution import QueryResolutionService

router = APIRouter(prefix="/synchronization", tags=["synchronization"])


async def _resolve_owned_approval(db: AsyncSession, user: dict, approval_id: str) -> Approval:
    try:
        pid = UUID(str(approval_id))
    except (ValueError, AttributeError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid approval id") from exc
    result = await db.execute(select(Approval).where(Approval.id == pid))
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Application not found")
    project_result = await db.execute(select(Project).where(Project.id == approval.project_id))
    project = project_result.scalar_one_or_none()
    if not project or str(project.user_id) != str(user["sub"]):
        raise HTTPException(status_code=403, detail="Not authorized")
    return approval


@router.post("/sync")
async def sync_all(
    user: dict = Depends(require_officer),
    db: AsyncSession = Depends(get_db_session),
):
    """Poll every tracked government application and reconcile status."""
    service = GovSyncService(db)
    return await service.sync_all()


@router.post("/{approval_id}/track")
async def track_application(
    approval_id: str,
    body: dict,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Link an approval to a government system + application id."""
    approval = await _resolve_owned_approval(db, user, approval_id)
    system = body.get("system")
    gov_app_id = body.get("government_application_id")
    if not system or not gov_app_id:
        raise HTTPException(status_code=400, detail="system and government_application_id required")
    record = await GovSyncService(db).track(approval, system, gov_app_id)
    return {
        "government_application_id": record.government_application_id,
        "system": record.system,
        "approval_id": str(approval.id),
    }


@router.get("/{approval_id}/query-resolution")
async def query_resolution(
    approval_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """AI-analyse a government query raised on an application (spec §20)."""
    approval = await _resolve_owned_approval(db, user, approval_id)
    service = QueryResolutionService(db)
    return await service.resolve_for_approval(approval)
