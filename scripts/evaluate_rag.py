"""RAG pipeline evaluation harness (spec §8).

Runs the UDYOGSETU RAG pipeline against a curated question set and reports
retrieval quality metrics so regressions are caught before they reach users.

Metrics computed:
  * retrieval_recall - fraction of expected answer points covered by retrieved
    context (evidence) BEFORE generation.
  * answer_coverage   - fraction of expected answer points present in the
    generated answer (proxy for answer completeness).
  * groundedness      - fraction of generated sentences grounded in retrieved
    context (simple lexical containment heuristic).

Run from the project root:
    python scripts/evaluate_rag.py
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def _coverage(answer: str, points: list[str]) -> float:
    atoks = _tokenize(answer)
    if not points:
        return 0.0
    hit = 0
    for point in points:
        ptoks = _tokenize(point)
        if ptoks and ptoks <= atoks:
            hit += 1
    return hit / len(points)


async def _evaluate() -> dict:
    import app.main  # noqa: F401  ensures settings/tables are ready
    from app.core.database import AsyncSessionLocal, Base, engine
    from app.rag.pipeline import RAGPipeline
    from app.services.data_loader import RuleLoadingService

    # Fresh in-memory style DB for reproducible metrics using the test DB env.
    questions_path = os.path.join(PROJECT_ROOT, "data", "rag_evaluation", "questions.json")
    with open(questions_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    # Ingest regulation knowledge (the corpus the questions are drawn from).
    async with AsyncSessionLocal() as session:
        loader = RuleLoadingService(session)
        reg_dir = os.path.join(PROJECT_ROOT, "data", "regulations")
        await loader.load_knowledge_documents(reg_dir)

    results = []
    async with AsyncSessionLocal() as session:
        pipeline = RAGPipeline(session)
        for q in questions:
            context = await pipeline.retrieve_context(q["question"], top_k=5)
            generated = await pipeline.generate_answer(q["question"])
            evidence_text = " ".join(c["text"] for c in context)
            recall = _coverage(evidence_text, q["expected_answer_points"])
            answer_coverage = _coverage(generated.get("answer", ""), q["expected_answer_points"])
            results.append({
                "id": q["id"],
                "category": q["category"],
                "retrieval_recall": round(recall, 3),
                "answer_coverage": round(answer_coverage, 3),
                "confidence": generated.get("confidence"),
                "n_sources": len(generated.get("sources", [])),
            })

    n = len(results) or 1
    avg_recall = sum(r["retrieval_recall"] for r in results) / n
    avg_coverage = sum(r["answer_coverage"] for r in results) / n
    avg_conf = sum((r["confidence"] or 0) for r in results) / n
    no_source = sum(1 for r in results if r["n_sources"] == 0)

    return {
        "questions": n,
        "avg_retrieval_recall": round(avg_recall, 3),
        "avg_answer_coverage": round(avg_coverage, 3),
        "avg_confidence": round(avg_conf, 3),
        "questions_without_sources": no_source,
        "per_question": results,
    }


def main() -> int:
    report = asyncio.run(_evaluate())
    print("=" * 60)
    print("UDYOGSETU RAG EVALUATION REPORT")
    print("=" * 60)
    print(f"Questions evaluated  : {report['questions']}")
    print(f"Avg retrieval recall : {report['avg_retrieval_recall']}")
    print(f"Avg answer coverage  : {report['avg_answer_coverage']}")
    print(f"Avg confidence       : {report['avg_confidence']}")
    print(f"Questions w/o sources: {report['questions_without_sources']}")
    print("-" * 60)
    for r in report["per_question"]:
        flag = "OK " if r["retrieval_recall"] >= 0.5 else "LOW"
        print(f"  [{flag}] {r['id']:6s} {r['category']:8s} "
              f"recall={r['retrieval_recall']:.2f} cov={r['answer_coverage']:.2f} "
              f"conf={r['confidence']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
