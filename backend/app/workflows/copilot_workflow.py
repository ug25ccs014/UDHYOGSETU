"""Copilot query-detection workflow.

Detects the intent of a free-text query and routes it to the right engine:

- Regulation lookup  -> RAG over the regulation knowledge base
- Document AI        -> cross-document validation summary
- Government status  -> live mock gateway status poll
- Scheme advice      -> incentive matcher
- General            -> the bundled LLM with project context

This mirrors the spec's "$21 Query Detection -> RAG -> Doc-AI" flow.
"""

from __future__ import annotations

import json
import logging
from uuid import UUID

from app.services.gateway_service import GatewayService
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

_INTENT_KEYWORDS: dict[str, list[str]] = {
    "regulation": [
        "regulation", "law", "rule", "act", "compliance", "license requirement",
        "legal", "statutory", "must i", "need to", "required", "obligation",
        "consent", "noc", "clearance",
    ],
    "document": [
        "document", "upload", "pan", "gstin", "gst registration", "validation",
        "cross", "mismatch", "expired", "expiry", "verify my document",
        "what documents", "documents do",
    ],
    "status": [
        "status", "application status", "track", "where is my application",
        "approval status", "how long", "sla", "pending approval",
    ],
    "scheme": [
        "scheme", "subsidy", "incentive", "grant", "benefit", "finance",
        "funding", "loan", "psu", "pmegp", "eligibility",
    ],
}


class CopilotWorkflow:
    """Route a query to the best answering engine with an intent label."""

    def __init__(self, db):
        self.db = db
        self.rag = RAGService(db)
        self.gateway = GatewayService()

    def detect_intent(self, question: str) -> str:
        lowered = (question or "").lower()
        best, best_score = "general", 0
        for intent, keywords in _INTENT_KEYWORDS.items():
            score = sum(1 for k in keywords if k in lowered)
            if score > best_score:
                best, best_score = intent, score
        return best

    async def route(self, question: str, project_id: UUID | None) -> dict:
        intent = self.detect_intent(question)
        try:
            if intent == "document" and project_id:
                return await self._document_flow(question, project_id, intent)
            if intent == "status" and project_id:
                return await self._status_flow(question, project_id, intent)
            if intent == "scheme" and project_id:
                return await self._scheme_flow(question, project_id, intent)
            # Default + regulation -> RAG. General queries may use tools.
            if intent == "general" and project_id:
                return await self._general_flow(question, project_id)
            return await self._regulation_flow(question, project_id, intent)
        except Exception as exc:
            logger.exception("Copilot workflow routing failed")
            return {
                "intent": intent,
                "engine": "error",
                "answer": "I ran into an error while processing your query. Please try again.",
                "error": str(exc),
                "sources": [],
                "confidence": 0.0,
            }

    async def _general_flow(self, question: str, project_id: UUID) -> dict:
        """Answer a general query using controlled tool calls (spec §11).

        The model is asked to pick relevant tools (as a structured JSON list);
        each chosen tool is executed against the allow-listed registry and the
        results are folded into a grounded, deterministic answer.
        """
        from app.ai.llm_provider import LLMProviderFactory
        from app.ai.tools import ToolCallingService
        from app.services.copilot_tools import get_copilot_tools

        registry = get_copilot_tools()
        schemas = registry.list()
        schema_json = json.dumps(schemas, indent=2)
        prompt = (
            "Given the user question and project id, choose which of these tools "
            "to call to best answer it. Respond ONLY with a JSON array of "
            f"{{'tool': <name>, 'args': {{...}}}}, using project_id {project_id!s} "
            "where needed. Empty array [] if no tool is relevant.\n\n"
            f"TOOLS:\n{schema_json}\n\nQUESTION: {question}"
        )
        provider = LLMProviderFactory.create()
        try:
            raw = await provider.structured_output(
                "You select tools. Return only valid JSON. Use the args documents provided.",
                prompt,
                temperature=0.0,
            )
            calls = raw.get("tool_calls") or raw.get("calls") or []
            if isinstance(raw, list):
                calls = raw
        except Exception:  # noqa: BLE001 - invalid/empty tool calls fall back to none
            calls = []

        service = ToolCallingService(registry, self.db)
        outputs = []
        for call in calls:
            if not isinstance(call, dict):
                continue
            tool = call.get("tool")
            args = call.get("args") or call.get("arguments") or {}
            args.setdefault("project_id", str(project_id))
            outputs.append(await service.execute(tool, args))

        results_block = json.dumps(outputs, indent=2, default=str)
        answer_prompt = (
            f"QUESTION: {question}\n\n"
            f"TOOL RESULTS:\n{results_block}\n\n"
            "Using ONLY the tool results above, write a concise, factual answer. "
            "If no tool result is relevant, say you need more specific details."
        )
        import time as _time

        from app.ai.llm_provider import generate_with_fallback
        from app.services.ai_observability import AIObservability
        obs = AIObservability(self.db)
        start = _time.perf_counter()
        try:
            answer = await generate_with_fallback(
                "You are UdyogSetu. Ground every claim in the provided tool results. Do not invent data.",
                answer_prompt,
                temperature=0.2,
            )
        except Exception:  # re-raise after logging the observability failure
            try:
                await obs.log_event(request_type="copilot_general", latency_ms=int((_time.perf_counter() - start) * 1000), success=False, error_kind="generation_failed")
            except Exception as obs_err:  # noqa: BLE001 - telemetry write must stay fire-and-forget
                logger.debug("AI observability failed event skipped: %s", obs_err)
            raise
        try:
            await obs.log_event(request_type="copilot_general", latency_ms=int((_time.perf_counter() - start) * 1000), success=True)
        except Exception as obs_err2:  # noqa: BLE001 - telemetry write must stay fire-and-forget
            logger.debug("AI observability success event skipped: %s", obs_err2)
        return {
            "intent": "general",
            "engine": "tools",
            "answer": answer,
            "sources": [{"title": "Live workspace data (controlled tools)"}],
            "confidence": 0.85,
            "tool_results": outputs,
        }

    async def _regulation_flow(self, question: str, project_id: UUID | None, intent: str) -> dict:
        result = await self.rag.answer_regulatory_question(question, project_id=project_id)
        return {
            "intent": intent,
            "engine": "rag",
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "confidence": result.get("confidence", 0),
        }

    async def _document_flow(self, question: str, project_id: UUID, intent: str) -> dict:
        from app.services.document_processor import DocumentProcessorService
        processor = DocumentProcessorService(self.db)
        cross = await processor.cross_validate(project_id)
        documents = await processor.list_project_documents(project_id)
        lines = []
        for d in documents:
            dt = (d.custom_metadata or {}).get("document_type") or "GENERIC"
            lines.append(f"- {d.file_name} ({dt}): {len(d.extracted_fields or {})} fields extracted")
        answer = (
            f"You have {len(documents)} uploaded document(s).\n"
            + "\n".join(lines)
            + f"\n\nCross-document validation: {cross['summary']} "
            f"({cross['summary']['red']} red, {cross['summary']['yellow']} yellow, {cross['summary']['green']} green findings)."
        )
        return {
            "intent": intent,
            "engine": "document_ai",
            "answer": answer,
            "sources": [{"title": "Cross-document validation"}],
            "confidence": 0.9,
            "cross_validation": cross.get("summary"),
        }

    async def _status_flow(self, question: str, project_id: UUID, intent: str) -> dict:
        from sqlalchemy import select

        from app.models import Approval
        result = await self.db.execute(
            select(Approval).where(Approval.project_id == project_id)
        )
        approvals = result.scalars().all()
        if not approvals:
            return {
                "intent": intent,
                "engine": "status",
                "answer": "No applications have been submitted yet. Start applying to see live status.",
                "sources": [],
                "confidence": 1.0,
            }
        lines = []
        for a in approvals[:8]:
            status = a.status.value if hasattr(a.status, "value") else str(a.status)
            lines.append(f"- {a.name}: {status}")
        answer = "Here is the status of your applications:\n" + "\n".join(lines) + "\n\nTrack them individually for live SLA updates from the department systems."
        return {"intent": intent, "engine": "status", "answer": answer, "sources": [], "confidence": 0.9}

    async def _scheme_flow(self, question: str, project_id: UUID, intent: str) -> dict:
        from app.services.incentive_matcher import IncentiveMatcher
        from app.services.project import ProjectService
        project = await ProjectService(self.db).get_project(project_id)
        if not project:
            return await self._regulation_flow(question, project_id, "general")
        project_data = {
            "sector": getattr(project, "sector", None),
            "location": getattr(project, "location", None),
            "investment_amount": getattr(project, "investment_amount", None),
            "employee_count": getattr(project, "employee_count", None),
            "project_type": getattr(project, "project_type", None),
        }
        matches = await IncentiveMatcher(self.db).find_matching_schemes({k: v for k, v in project_data.items() if v is not None})
        if not matches:
            answer = "No incentive matches found yet. Ensure your business details are complete."
        else:
            answer = f"I found {len(matches)} incentives you may qualify for.\n"
            for m in matches[:5]:
                answer += f"- {m.get('scheme_name', '')} (match {m.get('match_score', 0)}%)\n"
        return {"intent": intent, "engine": "scheme", "answer": answer, "sources": [], "confidence": 0.8}