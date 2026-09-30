"""Tests for the RAG evaluation harness and regulatory versioning (spec §8, §9)."""

import json
import os

import pytest

from app.core.database import AsyncSessionLocal
from app.models import KnowledgeChunk, KnowledgeDocument
from app.rag.pipeline import RAGPipeline, _coerce_datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
QUESTIONS_PATH = os.path.join(PROJECT_ROOT, "data", "rag_evaluation", "questions.json")


@pytest.fixture(autouse=True)
async def _cleanup():
    yield
    async with AsyncSessionLocal() as db:
        await db.execute(KnowledgeChunk.__table__.delete())
        await db.execute(KnowledgeDocument.__table__.delete())
        await db.commit()


def test_questions_file_is_valid():
    assert os.path.exists(QUESTIONS_PATH)
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        questions = json.load(f)
    assert len(questions) >= 50, "expected at least 50 evaluation questions (spec §8)"
    for q in questions:
        assert q["question"]
        assert q["expected_answer_points"]
        assert q["expected_source_hint"]


async def _ingest(db, title, text, metadata):
    pipeline = RAGPipeline(db)
    return await pipeline.ingest_document(title, text, metadata)


async def test_retrieval_excludes_superseded_versions():
    """A regulation version with a past effective_to is not retrieved."""
    from datetime import datetime, timedelta
    async with AsyncSessionLocal() as db:
        await _ingest(
            db, "Old Boiler Rule v1",
            "Every steam boiler above 22.75 litres must be registered. This is the old rule.",
            {"document_type": "REGULATION", "department": "Boiler", "version": "v1"},
        )
        await _ingest(
            db, "Old Boiler Rule v2",
            "Every steam boiler above 22.75 litres must be registered. Renewed rule.",
            {
                "document_type": "REGULATION",
                "department": "Boiler",
                "version": "v2",
                "effective_to": (datetime.utcnow() - timedelta(days=30)),
            },
        )
        await db.commit()

    async with AsyncSessionLocal() as db:
        ctx = await RAGPipeline(db).retrieve_context("boiler registration litres", top_k=10)
    # The superseded version (past effective_to) must not appear.
    assert all("Renewed rule" not in c["text"] for c in ctx)


def test_coerce_datetime():
    assert _coerce_datetime(None) is None
    assert _coerce_datetime("2024-01-01T00:00:00Z") is not None
    assert _coerce_datetime("garbage") is None
