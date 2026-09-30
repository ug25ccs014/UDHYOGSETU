"""AI document explanation — spec §16.

Takes the deterministic cross-document validation findings (GREEN/YELLOW/RED)
that ``CrossDocumentValidator`` produces and turns them into plain-language,
actionable narratives via the LLM provider. On maker machines the mock
provider produces grounded, deterministic narratives straight from the finding
data; with a hosted provider the same prompt yields richer prose — but never
invents beyond the findings.

The service is deliberately read-only and returns explanations alongside the
original findings so the UI can show "what" plus "why it matters / what to do".
"""

from __future__ import annotations

import logging
from typing import Any

from app.ai.llm_provider import LLMProviderFactory

logger = logging.getLogger(__name__)

_FINDING_ACTION: dict[str, str] = {
    "name": (
        "The company/organisation name differs across the documents. Obtain a "
        "corrected copy or a supporting letter so all records match the legal name."
    ),
    "address": (
        "The registered address differs across the documents. Confirm the "
        "official registered address and re-upload consistent proof."
    ),
    "expiry": (
        "At least one document has expired. Renew the document before it is "
        "needed for any approval application."
    ),
}

_LEVEL_INTRO: dict[str, str] = {
    "GREEN": "consistent",
    "YELLOW": "needs your attention",
    "RED": "blocks your application",
}


class DocumentExplanationService:
    """Generate human-readable explanations for validation findings."""

    async def explain_findings(self, findings: list[dict[str, Any]]) -> dict[str, Any]:
        if not findings:
            return {
                "summary": "All uploaded documents are consistent — no validation issues found.",
                "items": [],
            }

        # Build a compact, deterministic representation for the LLM.
        rows = []
        for f in findings:
            rows.append(
                f"[{f.get('level', 'YELLOW')}] field={f.get('field')} "
                f"message={f.get('message')}"
            )
        findings_block = "\n".join(rows)

        system_prompt = (
            "You are UdyogSetu; you help an entrepreneur understand their "
            "document validation. Explain each finding in simple, non-legal "
            "language. State the severity clearly. For each issue, give a "
            "concrete next action. Do not invent findings beyond the list."
        )
        prompt = (
            "Here are the cross-document validation findings:\n\n"
            f"{findings_block}\n\n"
            "Return a JSON array of explanations, one per finding, each with "
            "\"field\", \"severity\", \"explanation\", and \"action\". "
            "Keep each explanation under two sentences."
        )

        items = await self._generate_explanations(system_prompt, prompt, findings)

        reds = sum(1 for f in findings if f.get("level") == "RED")
        yellows = sum(1 for f in findings if f.get("level") == "YELLOW")

        if reds:
            summary = (
                f"{reds} critical and {yellows} attention issues found. "
                "Fix the critical mismatches before proceeding with approvals."
            )
        elif yellows:
            summary = f"{yellows} attention item(s) found — fix them to avoid delays."
        else:
            summary = "All documents are consistent."

        return {"summary": summary, "items": items}

    async def _generate_explanations(self, system_prompt: str, prompt: str, findings: list) -> list:
        """Produce per-finding explanations, with deterministic fallback."""
        try:
            provider = LLMProviderFactory.create()
            parsed = await provider.structured_output(system_prompt, prompt, temperature=0.2)
            parsed_items = parsed.get("items") or parsed.get("explanations") or []
            if parsed.get("raw") and not parsed_items:
                parsed_items = []
            parsed_items = [i for i in parsed_items if isinstance(i, dict)]
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM document explanation failed: %s", exc)
            parsed_items = []

        # Fall back to a deterministic narrative if the LLM produced nothing usable.
        if not parsed_items:
            return self._deterministic_explanations(findings)

        # Merge/align with the deterministic actions for missing fields.
        merged = []
        for i, f in enumerate(findings):
            item = parsed_items[i] if i < len(parsed_items) else {}
            merged.append({
                "field": item.get("field") or f.get("field") or "document",
                "severity": item.get("severity") or f.get("level") or "YELLOW",
                "explanation": item.get("explanation") or f.get("message"),
                "action": item.get("action") or self._action_for(f),
            })
        return merged

    def _deterministic_explanations(self, findings: list) -> list:
        items = []
        for f in findings:
            severity = f.get("level") or "YELLOW"
            items.append({
                "field": f.get("field"),
                "severity": severity,
                "explanation": f.get("message"),
                "action": self._action_for(f),
            })
        return items

    @staticmethod
    def _action_for(finding: dict) -> str:
        field = (finding.get("field") or "").lower()
        return _FINDING_ACTION.get(
            field,
            f"Review and correct the {finding.get('field') or 'document detail'} issue.",
        )
