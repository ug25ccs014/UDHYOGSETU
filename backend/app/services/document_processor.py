import asyncio
import os
import re
import uuid
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Document, DocumentStatus
from app.services.document_intelligence import DocumentIntelligenceService


def _write_bytes(file_path: str, contents: bytes) -> None:
    with open(file_path, "wb") as f:
        f.write(contents)

ALLOWED_TYPES = {
    "application/pdf": {".pdf"},
    "image/png": {".png"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/webp": {".webp"},
    "text/plain": {".txt", ".log", ".md"},
    "application/msword": {".doc"},
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {".docx"},
    "application/vnd.ms-excel": {".xls"},
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {".xlsx"},
    "text/csv": {".csv"},
}

_SAFE_RE = re.compile(r"[^A-Za-z0-9_.\- ]")


def _sanitize_filename(filename: str) -> str:
    """Return a safe basename with the original extension preserved."""
    base = os.path.basename(filename or "").replace("\\", "/").split("/")[-1]
    base = _SAFE_RE.sub("_", base).strip(" ._")
    if not base:
        base = "document"
    return base


class DocumentProcessorService:
    """Document processing and intelligence service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def process_uploaded_file(self, project_id: UUID, file: UploadFile) -> Document:
        """Process uploaded document"""
        contents = await file.read()
        if len(contents) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise ValueError(
                f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB} MB"
            )

        safe_name = _sanitize_filename(file.filename or "")
        ext = os.path.splitext(safe_name)[1].lower()
        allowed_ext = ALLOWED_TYPES.get(file.content_type or "")
        if not allowed_ext or ext not in allowed_ext:
            raise ValueError(
                f"Unsupported file type '{file.content_type}'. Allowed: "
                + ", ".join(sorted(ALLOWED_TYPES))
            )

        upload_dir = os.path.join(settings.UPLOAD_DIRECTORY, str(project_id))
        os.makedirs(upload_dir, exist_ok=True)

        stored_name = f"{uuid.uuid4().hex}_{safe_name}"
        file_path = os.path.join(upload_dir, stored_name)

        await asyncio.to_thread(_write_bytes, file_path, contents)

        # Run document intelligence: extract text, OCR, classify, extract fields.
        intelligence = DocumentIntelligenceService(self.db)
        extracted_text = intelligence.extract_text_from_file(
            file_path, file.content_type or ""
        )
        extracted_fields = intelligence.extract_fields(extracted_text) if extracted_text else {}
        validation_errors = intelligence.validate_document_fields(extracted_fields) if extracted_text else []

        if extracted_text and not validation_errors:
            status = DocumentStatus.VERIFIED
        elif extracted_text and validation_errors:
            status = (
                DocumentStatus.EXPIRED
                if any("expired" in str(error).lower() for error in validation_errors)
                else DocumentStatus.WARNING
            )
        else:
            status = DocumentStatus.UPLOADED

        document = Document(
            project_id=project_id,
            file_name=safe_name,
            file_path=file_path,
            file_type=file.content_type or "application/octet-stream",
            file_size=len(contents),
            status=status,
            extracted_text=extracted_text[:20000] if extracted_text else None,
            extracted_fields=extracted_fields,
            validation_errors=validation_errors,
            custom_metadata={
                "stored_name": stored_name,
                "document_type": extracted_fields.get("document_type"),
            },
        )

        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)

        return document

    async def get_document(self, document_id: UUID) -> Document:
        """Get document details"""
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    async def validate_document(self, document_id: UUID) -> dict:
        """Validate a document, refresh extracted fields and set a readiness status."""
        document = await self.get_document(document_id)
        if not document:
            return {"error": "Document not found"}

        intelligence = DocumentIntelligenceService(self.db)
        extracted_text = document.extracted_text

        # If nothing was extracted on upload, retry extraction now.
        if not extracted_text and document.file_path and os.path.exists(document.file_path):
            extracted_text = await asyncio.to_thread(
                intelligence.extract_text_from_file, document.file_path, document.file_type
            )
            if extracted_text:
                document.extracted_text = extracted_text[:20000]

        if extracted_text:
            document.extracted_fields = intelligence.extract_fields(extracted_text)
            document.validation_errors = intelligence.validate_document_fields(document.extracted_fields)
            document.status = (
                DocumentStatus.EXPIRED
                if any("expired" in str(error).lower() for error in document.validation_errors)
                else DocumentStatus.WARNING
                if document.validation_errors
                else DocumentStatus.VERIFIED
            )
            document.custom_metadata = {
                **(document.custom_metadata or {}),
                "document_type": document.extracted_fields.get("document_type"),
            }
            await self.db.commit()
            await self.db.refresh(document)

        return {
            "document_id": str(document_id),
            "status": document.status,
            "extracted_fields": document.extracted_fields,
            "validation_errors": document.validation_errors,
            "extracted_text_preview": (document.extracted_text or "")[:1000],
            "document_type": (document.custom_metadata or {}).get("document_type"),
        }

    async def list_project_documents(self, project_id: UUID) -> list[Document]:
        """List all documents uploaded for a project."""
        result = await self.db.execute(
            select(Document).where(Document.project_id == project_id).order_by(Document.created_at.desc())
        )
        return result.scalars().all()

    async def cross_validate(self, project_id: UUID) -> dict:
        """Run cross-document validation across all of a project's documents."""
        docs = await self.list_project_documents(project_id)
        payloads = []
        for d in docs:
            if d.extracted_fields:
                payloads.append({"id": str(d.id), "name": d.file_name, "extracted_fields": dict(d.extracted_fields or {})})
        from app.services.document_intelligence import CrossDocumentValidator
        findings = CrossDocumentValidator().validate(payloads)
        return {
            "project_id": str(project_id),
            "documents_validated": len(payloads),
            "findings": findings,
            "summary": {
                "green": sum(1 for f in findings if f["level"] == "GREEN"),
                "yellow": sum(1 for f in findings if f["level"] == "YELLOW"),
                "red": sum(1 for f in findings if f["level"] == "RED"),
            },
        }