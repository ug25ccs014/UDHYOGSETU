import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_owned_document, require_project_owner
from app.core.database import get_db_session
from app.schemas import DocumentResponse
from app.services.document_processor import DocumentProcessorService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    project_id: UUID,
    file: UploadFile = File(...),
    user: None = Depends(require_project_owner),
    db: AsyncSession = Depends(get_db_session)
):
    """Upload and process document"""
    processor = DocumentProcessorService(db)
    try:
        document = await processor.process_uploaded_file(project_id, file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return document

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    document: object = Depends(get_owned_document),
):
    """Get document details and extracted information"""
    return document

@router.post("/{document_id}/validate")
async def validate_document(
    document_id: UUID,
    document: object = Depends(get_owned_document),
    db: AsyncSession = Depends(get_db_session)
):
    """Validate document and extract fields"""
    processor = DocumentProcessorService(db)
    validation_result = await processor.validate_document(document_id)
    return validation_result

@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: UUID,
    document: object = Depends(get_owned_document),
):
    """Kick off async OCR/extraction/RAG-ingest for a document as a background job."""
    from app.workers.background import get_task_manager
    from app.workers.tasks import process_document_task
    job_id = get_task_manager().submit(
        lambda doc_id=document_id: process_document_task(doc_id),
        name="process_document",
    )
    return {"job_id": job_id, "status": "PENDING", "document_id": str(document_id)}


@router.get("/project/{project_id}/cross-validate")
async def cross_validate_project_documents(
    project_id: UUID,
    project: object = Depends(require_project_owner),
    db: AsyncSession = Depends(get_db_session),
):
    """Run cross-document validation across a project's documents."""
    processor = DocumentProcessorService(db)
    result = await processor.cross_validate(project_id)
    return result


@router.get("/project/{project_id}/cross-validate/explain")
async def explain_project_documents(
    project_id: UUID,
    project: object = Depends(require_project_owner),
    db: AsyncSession = Depends(get_db_session),
):
    """Cross-document validation plus AI explanations (spec §16)."""
    processor = DocumentProcessorService(db)
    cross = await processor.cross_validate(project_id)
    from app.services.document_explanation import DocumentExplanationService
    explanation = await DocumentExplanationService().explain_findings(cross.get("findings", []))
    try:
        from app.services.ai_observability import AIObservability
        await AIObservability(db).log_event(request_type="document_explanation", project_id=project_id, success=True)
    except Exception as exc:  # noqa: BLE001 - telemetry must never break the response
        logger.debug("AI observability event skipped: %s", exc)
    return {
        **cross,
        "explanation": explanation,
    }