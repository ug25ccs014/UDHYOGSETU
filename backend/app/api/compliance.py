from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_project_owner
from app.core.database import get_db_session
from app.core.security import get_current_user
from app.schemas import ComplianceItemComplete, RenewalUpdate
from app.services.compliance import ComplianceService
from app.services.compliance_lifecycle import ComplianceLifecycleService

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.get("/renewals/{renewal_id}")
async def get_renewal(
    renewal_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await ComplianceLifecycleService(db).renewal_detail(renewal_id, UUID(str(user["sub"])))
    except ValueError as exc:
        status = 404 if "not found" in str(exc).lower() else 403
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.patch("/renewals/{renewal_id}")
async def update_renewal(
    renewal_id: UUID,
    payload: RenewalUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await ComplianceLifecycleService(db).update_renewal(
            renewal_id,
            UUID(str(user["sub"])),
            status=payload.status,
            external_reference=payload.external_reference,
            notes=payload.notes,
            document_ids=payload.document_ids,
        )
    except ValueError as exc:
        status = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.get("/{project_id}/renewals")
async def get_renewals(
    project_id: UUID,
    project: object = Depends(require_project_owner),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    return {
        "renewals": await ComplianceLifecycleService(db).list_renewals(
            project_id, UUID(str(user["sub"]))
        )
    }


@router.post("/{project_id}/renewals/{approval_id}/prepare")
async def prepare_renewal(
    project_id: UUID,
    approval_id: UUID,
    project: object = Depends(require_project_owner),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await ComplianceLifecycleService(db).prepare_renewal(
            project_id, approval_id, UUID(str(user["sub"]))
        )
    except ValueError as exc:
        status = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.post("/items/{item_id}/complete")
async def complete_compliance_item(
    item_id: UUID,
    payload: ComplianceItemComplete,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await ComplianceLifecycleService(db).complete_item(
            item_id,
            UUID(str(user["sub"])),
            payload.completed_at,
        )
    except ValueError as exc:
        status = 404 if "not found" in str(exc).lower() else 403
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.get("/{project_id}/items")
async def get_compliance_items(
    project_id: UUID,
    project: object = Depends(require_project_owner),
    db: AsyncSession = Depends(get_db_session),
):
    service = ComplianceService(db)
    await service.ensure_compliance_items(project_id)
    return await service.get_compliance_items(project_id)


@router.get("/{project_id}")
async def get_compliance_dashboard(
    project_id: UUID,
    project: object = Depends(require_project_owner),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get lifecycle dashboard with actionable tasks and renewal cases."""
    return await ComplianceLifecycleService(db).dashboard(
        project_id, UUID(str(user["sub"]))
    )
