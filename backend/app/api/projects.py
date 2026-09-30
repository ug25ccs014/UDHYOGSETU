from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_owned_project
from app.core.database import get_db_session
from app.core.security import get_current_user
from app.rules.approval_engine import ApprovalEngine
from app.schemas import ApprovalResponse, ProjectOnboarding, ProjectResponse
from app.services.project import UPDATABLE_FIELDS, ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse)
async def create_project(
    project_data: ProjectOnboarding,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    service = ProjectService(db)
    project = await service.create_project(project_data, user_id=UUID(user["sub"]))
    return project


@router.get("", response_model=list[ProjectResponse])
async def list_my_projects(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """List all projects owned by the authenticated user"""
    service = ProjectService(db)
    projects = await service.list_user_projects(UUID(user["sub"]))
    return projects


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    project: object = Depends(get_owned_project),
):
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    update_data: dict,
    project: object = Depends(get_owned_project),
    db: AsyncSession = Depends(get_db_session),
):
    allowed_fields = {k: v for k, v in update_data.items() if k in UPDATABLE_FIELDS}
    unknown = set(update_data) - UPDATABLE_FIELDS
    if unknown and len(unknown) == len(update_data):
        raise HTTPException(status_code=400, detail=f"No updatable fields provided. Allowed: {sorted(UPDATABLE_FIELDS)}")
    service = ProjectService(db)
    updated = await service.update_project(project_id, allowed_fields)
    return updated


@router.post("/{project_id}/analyze")
async def analyze_project(
    project_id: UUID,
    project: object = Depends(get_owned_project),
    db: AsyncSession = Depends(get_db_session),
):
    """Analyze project and determine applicable approvals"""
    engine = ApprovalEngine(db)
    approvals = await engine.determine_approvals(project.id)
    return {
        "project_id": project.id,
        "applicable_approvals": approvals,
        "total_count": len(approvals),
        "mandatory_count": sum(1 for a in approvals if a["is_mandatory"])
    }


@router.get("/{project_id}/approvals", response_model=list[ApprovalResponse])
async def get_project_approvals(
    project_id: UUID,
    project: object = Depends(get_owned_project),
    db: AsyncSession = Depends(get_db_session),
):
    service = ProjectService(db)
    approvals = await service.get_project_approvals(project.id)
    return approvals


@router.get("/{project_id}/approval-graph")
async def get_approval_graph(
    project_id: UUID,
    project: object = Depends(get_owned_project),
    db: AsyncSession = Depends(get_db_session),
):
    """Return the approval dependency graph + critical path for a project."""
    from app.services.approval_graph import ApprovalGraphService
    service = ApprovalGraphService(db)
    graph = await service.build_graph(project.id)
    return graph


@router.get("/{project_id}/documents")
async def get_project_documents(
    project_id: UUID,
    project: object = Depends(get_owned_project),
    db: AsyncSession = Depends(get_db_session),
):
    from app.services.document_processor import DocumentProcessorService
    processor = DocumentProcessorService(db)
    documents = await processor.list_project_documents(project.id)
    return [
        {
            "id": str(d.id),
            "file_name": d.file_name,
            "file_type": d.file_type,
            "status": d.status.value if hasattr(d.status, "value") else str(d.status),
            "document_type": (d.custom_metadata or {}).get("document_type"),
            "extracted_fields": d.extracted_fields,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in documents
    ]