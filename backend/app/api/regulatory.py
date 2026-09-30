from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_project_owner
from app.core.database import get_db_session
from app.core.security import get_current_user
from app.services.gateway_service import GatewayService
from app.integrations.government_adapters import system_for_department
from app.models import Approval
from app.rag.pipeline import RAGPipeline

router = APIRouter(prefix="/regulatory", tags=["regulatory"])


class RegulatoryQuery(BaseModel):
    query: str
    project_id: str


class GovernmentSubmission(BaseModel):
    system: str
    data: dict = {}


def _parse_project_id(project_id: str) -> UUID | None:
    try:
        return UUID(project_id)
    except (ValueError, AttributeError, TypeError):
        return None


@router.post("/query")
async def query_regulatory_knowledge(
    req: RegulatoryQuery,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    project_id = _parse_project_id(req.project_id)
    if project_id:
        await require_project_owner(project_id, user, db)

    pipeline = RAGPipeline(db)
    result = await pipeline.generate_answer(req.query)
    return {
        "query": req.query,
        "answer": result["answer"],
        "confidence": result["confidence"],
        "sources": result["sources"],
        "evidence": result["evidence"],
    }


@router.post("/chat")
async def chat_with_copilot(
    req: RegulatoryQuery,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    project_id = _parse_project_id(req.project_id)
    if project_id:
        await require_project_owner(project_id, user, db)

    pipeline = RAGPipeline(db)
    result = await pipeline.generate_answer(req.query)
    return {
        "response": result["answer"],
        "confidence": result["confidence"],
        "sources": result["sources"],
    }


@router.get("/government/{system}/status/{application_id}")
async def get_government_status(
    system: str,
    application_id: str,
    user: dict = Depends(get_current_user),
):
    gateway = GatewayService()
    try:
        result = await gateway.get_status(system, application_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/government/submit")
async def submit_to_government(
    req: GovernmentSubmission,
    user: dict = Depends(get_current_user),
):
    gateway = GatewayService()
    try:
        result = await gateway.submit(req.system, req.data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/government/all-statuses/{project_id}")
async def get_all_government_statuses(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    project_uuid = _parse_project_id(project_id)
    if not project_uuid:
        raise HTTPException(status_code=404, detail="Project not found")

    await require_project_owner(project_uuid, user, db)

    result = await db.execute(
        select(Approval).where(Approval.project_id == project_uuid)
    )
    approvals = result.scalars().all()

    gateway = GatewayService()

    app_ids = {}
    for approval in approvals:
        system = system_for_department(approval.department)
        descriptor = gateway.descriptor(system or "") if system else None
        if system and descriptor and descriptor["supports_status"]:
            app_ids[system] = approval.application_id or f"{system}-pending"

    statuses = await gateway.get_all_statuses(app_ids)

    return {
        "project_id": project_id,
        "statuses": statuses,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/change/recent")
async def recent_regulatory_changes(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    limit: int = 20,
    department: str | None = None,
    effective_status: str | None = None,
):
    """List recent version changes with effective-date and potential-impact signals."""
    from app.services.regulatory_change import RegulatoryChangeService

    changes = await RegulatoryChangeService(db).recent_changes(
        limit=min(max(limit, 1), 100),
        department=department,
        effective_status=effective_status,
    )
    return {
        "changes": changes,
        "count": len(changes),
        "filters": {
            "department": department,
            "effective_status": effective_status,
            "limit": min(max(limit, 1), 100),
        },
        "disclaimer": (
            "Regulatory updates are advisory summaries from the configured knowledge base. "
            "Potential impact does not constitute a statutory determination or legal advice."
        ),
    }


@router.get("/change/project/{project_id}")
async def project_regulatory_changes(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    limit: int = 20,
):
    """List recent regulatory changes that may affect an applicant's own project."""
    project_uuid = _parse_project_id(project_id)
    if not project_uuid:
        raise HTTPException(status_code=400, detail="Invalid project id")
    await require_project_owner(project_uuid, user, db)

    from app.services.regulatory_change import RegulatoryChangeService

    changes = await RegulatoryChangeService(db).project_changes(
        project_uuid, limit=min(max(limit, 1), 100)
    )
    return {
        "project_id": project_id,
        "changes": changes,
        "count": len(changes),
        "disclaimer": (
            "Potential project impact is an advisory metadata match. It does not determine "
            "whether a legal requirement applies to the project."
        ),
    }


@router.get("/change/{document_id}")
async def regulatory_change_diff(
    document_id: str,
    project_id: str | None = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Describe a regulation change and optionally evaluate impact on an owned project."""
    from app.services.regulatory_change import RegulatoryChangeService
    doc_uuid = UUID(document_id) if _valid_uuid(document_id) else None
    if not doc_uuid:
        raise HTTPException(status_code=400, detail="Invalid document id")

    project_uuid = None
    if project_id:
        project_uuid = _parse_project_id(project_id)
        if not project_uuid:
            raise HTTPException(status_code=400, detail="Invalid project id")
        await require_project_owner(project_uuid, user, db)

    result = await RegulatoryChangeService(db).diff(doc_uuid, project_id=project_uuid)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


def _valid_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False