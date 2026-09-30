from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_auth, require_project_owner
from app.core.database import get_db_session
from app.core.security import get_current_user
from app.models import Scheme
from app.schemas import IncentiveApplicationPrepare, IncentiveApplicationUpdate
from app.services.incentive_readiness import IncentiveReadinessService

router = APIRouter(prefix="/schemes", tags=["schemes"])


@router.get("")
async def list_schemes(
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
):
    """List the configured incentive catalogue."""
    result = await db.execute(
        select(Scheme)
        .where(Scheme.is_active == True)
        .order_by(Scheme.name)
    )
    schemes = result.scalars().all()
    return {
        "schemes": [
            {
                "id": str(scheme.id),
                "name": scheme.name,
                "department": scheme.department,
                "sector": scheme.sector,
                "location": scheme.location,
                "min_investment": scheme.min_investment,
                "max_investment": scheme.max_investment,
                "eligible_entity": scheme.eligible_entity,
                "employee_requirement": scheme.employee_requirement,
                "benefits": scheme.benefits or [],
                "application_period": scheme.application_period,
                "required_documents": scheme.required_documents or [],
                "source": scheme.source,
                "source_url": scheme.source_url,
            }
            for scheme in schemes
        ]
    }


@router.get("/projects/{project_id}/readiness")
async def project_incentive_readiness(
    project_id: UUID,
    project: object = Depends(require_project_owner),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(20, ge=1, le=50),
):
    """Return matched schemes enriched with application-readiness information."""
    return await IncentiveReadinessService(db).project_readiness(
        project_id, UUID(str(user["sub"])), limit=limit
    )


@router.get("/projects/{project_id}/{scheme_id}/readiness")
async def scheme_incentive_readiness(
    project_id: UUID,
    scheme_id: UUID,
    project: object = Depends(require_project_owner),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Return detailed readiness for one scheme/project combination."""
    try:
        return await IncentiveReadinessService(db).scheme_readiness(
            project_id, scheme_id, UUID(str(user["sub"]))
        )
    except ValueError as exc:
        status = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.post("/projects/{project_id}/{scheme_id}/prepare")
async def prepare_incentive_application(
    project_id: UUID,
    scheme_id: UUID,
    payload: IncentiveApplicationPrepare,
    project: object = Depends(require_project_owner),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create/update an internal preparation case; no government submission occurs."""
    try:
        return await IncentiveReadinessService(db).prepare_case(
            project_id,
            scheme_id,
            UUID(str(user["sub"])),
            document_ids=payload.document_ids,
            notes=payload.notes,
        )
    except ValueError as exc:
        status = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.get("/incentive-cases/{case_id}")
async def get_incentive_case(
    case_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await IncentiveReadinessService(db).case_detail(
            case_id, UUID(str(user["sub"]))
        )
    except ValueError as exc:
        status = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.patch("/incentive-cases/{case_id}")
async def update_incentive_case(
    case_id: UUID,
    payload: IncentiveApplicationUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await IncentiveReadinessService(db).update_case(
            case_id,
            UUID(str(user["sub"])),
            status=payload.status,
            document_ids=payload.document_ids,
            notes=payload.notes,
            external_reference=payload.external_reference,
        )
    except ValueError as exc:
        status = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc
