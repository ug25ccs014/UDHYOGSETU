"""Ready-made background task functions for the worker pool."""

from __future__ import annotations

import logging
from uuid import UUID

from app.core.database import AsyncSessionLocal
from app.rag.pipeline import RAGPipeline
from app.models import DocumentStatus
from app.services.document_intelligence import DocumentIntelligenceService
from app.services.document_processor import DocumentProcessorService

logger = logging.getLogger(__name__)


async def process_document_task(document_id: str | UUID) -> dict:
    """OCR + field-extraction + ingestion, run outside the request path."""
    async with AsyncSessionLocal() as db:
        processor = DocumentProcessorService(db)
        doc = await processor.get_document(UUID(str(document_id)))
        if not doc:
            return {"document_id": str(document_id), "error": "not found"}

        intelligence = DocumentIntelligenceService(db)
        if not doc.extracted_text and doc.file_path:
            text = intelligence.extract_text_from_file(doc.file_path, doc.file_type)
            if text:
                doc.extracted_text = text[:20000]

        if doc.extracted_text:
            doc.extracted_fields = intelligence.extract_fields(doc.extracted_text)
            doc.validation_errors = intelligence.validate_document_fields(doc.extracted_fields)
            doc.status = (
                DocumentStatus.EXPIRED
                if any("expired" in str(error).lower() for error in doc.validation_errors)
                else DocumentStatus.WARNING
                if doc.validation_errors
                else DocumentStatus.VERIFIED
            )
            doc.custom_metadata = {
                **(doc.custom_metadata or {}),
                "document_type": doc.extracted_fields.get("document_type"),
            }
            await db.commit()
            await db.refresh(doc)

        # Best-effort ingest into the RAG knowledge store.
        if doc.extracted_text:
            try:
                pipeline = RAGPipeline(db)
                await pipeline.ingest_document(
                    doc.file_name,
                    doc.extracted_text,
                    {"document_type": (doc.custom_metadata or {}).get("document_type"), "department": None},
                )
            except Exception:  # noqa: BLE001
                logger.warning("RAG ingest failed for document %s", doc.id)

        return {
            "document_id": str(doc.id),
            "extracted": bool(doc.extracted_text),
            "document_type": (doc.custom_metadata or {}).get("document_type"),
        }
