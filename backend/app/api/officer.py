"""Officer analytics API."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_officer
from app.core.database import get_db_session
from app.services.officer_analytics import OfficerAnalyticsService

router = APIRouter(prefix="/officer", tags=["officer-analytics"])


@router.get("/overview")
async def officer_overview(
    user: dict = Depends(require_officer),
    db: AsyncSession = Depends(get_db_session),
):
    svc = OfficerAnalyticsService(db)
    return await svc.overview()


@router.get("/by-department")
async def officer_by_department(
    user: dict = Depends(require_officer),
    db: AsyncSession = Depends(get_db_session),
):
    svc = OfficerAnalyticsService(db)
    return {"departments": await svc.by_department()}


@router.get("/status-distribution")
async def officer_status_distribution(
    user: dict = Depends(require_officer),
    db: AsyncSession = Depends(get_db_session),
):
    svc = OfficerAnalyticsService(db)
    return {"distribution": await svc.status_distribution()}


@router.get("/full")
async def officer_full_dashboard(
    user: dict = Depends(require_officer),
    db: AsyncSession = Depends(get_db_session),
):
    svc = OfficerAnalyticsService(db)
    return {
        "overview": await svc.overview(),
        "departments": await svc.by_department(),
        "distribution": await svc.status_distribution(),
    }

@router.get("/command-center")
async def officer_command_center(
    department: str | None = None,
    risk_band: str | None = None,
    limit: int = Query(default=25, ge=1, le=100),
    user: dict = Depends(require_officer),
    db: AsyncSession = Depends(get_db_session),
):
    """Return the live officer command-center snapshot.

    This is an operational aggregation over the existing officer analytics and
    SLA-risk services; it does not change application workflow state.
    """
    svc = OfficerAnalyticsService(db)
    return await svc.command_center(
        department=department,
        risk_band=risk_band,
        limit=limit,
    )
