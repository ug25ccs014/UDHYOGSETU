"""SLA + smart-risk command center APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_officer, require_project_owner
from app.core.database import get_db_session
from app.core.security import get_current_user
from app.services.sla_risk import SlaRiskService

router = APIRouter(prefix="/sla-risk", tags=["sla-risk"])


@router.get("/portfolio")
async def sla_risk_portfolio(
    project_id: UUID | None = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Applicant-facing SLA/risk portfolio across owned projects."""
    if project_id is not None:
        # Explicit owner dependency is intentionally checked here instead of
        # relying on the query filter alone so access errors are not ambiguous.
        from app.models import Project
        from sqlalchemy import select

        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project or str(project.user_id) != str(user["sub"]):
            raise HTTPException(status_code=403, detail="Not authorized to access this project")
    return await SlaRiskService(db).portfolio(UUID(user["sub"]), project_id)


@router.get("/project/{project_id}")
async def sla_risk_project(
    project_id: UUID,
    project: object = Depends(require_project_owner),
    db: AsyncSession = Depends(get_db_session),
):
    """SLA/risk view for one entrepreneur-owned project."""
    return await SlaRiskService(db).portfolio(UUID(str(project.user_id)), project_id)


@router.get("/application/{application_id}")
async def sla_risk_application(
    application_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Single enriched SLA/risk view for an application.

    Entrepreneurs can access their own applications. Officers/admins can access
    the same operational view for review without changing application state.
    """
    from sqlalchemy import select
    from app.models import Approval, Project

    result = await db.execute(select(Approval).where(Approval.application_id == application_id))
    approval = result.scalar_one_or_none()
    if not approval:
        try:
            result = await db.execute(select(Approval).where(Approval.id == UUID(application_id)))
            approval = result.scalar_one_or_none()
        except (ValueError, AttributeError, TypeError):
            approval = None
    if not approval:
        raise HTTPException(status_code=404, detail="Application not found")

    project = (await db.execute(select(Project).where(Project.id == approval.project_id))).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    role = str(user.get("role", ""))
    if role not in {"OFFICER", "ADMIN"} and str(project.user_id) != str(user["sub"]):
        raise HTTPException(status_code=403, detail="Not authorized to access this application")

    return await SlaRiskService(db).evaluate_approval(approval, project)


@router.get("/officer")
async def officer_sla_risk_queue(
    department: str | None = None,
    risk_band: str | None = Query(default=None, alias="risk"),
    limit: int = Query(default=50, ge=1, le=200),
    user: dict = Depends(require_officer),
    db: AsyncSession = Depends(get_db_session),
):
    """Officer/admin operational SLA risk queue."""
    return await SlaRiskService(db).officer_queue(
        department=department,
        risk_band=risk_band,
        limit=limit,
    )
