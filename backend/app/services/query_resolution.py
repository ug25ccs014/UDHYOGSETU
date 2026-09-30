"""Government-query resolution workflow for entrepreneur applications.

The service keeps the existing gateway/RAG/Doc-AI capabilities but adds a
persisted query-response lifecycle so an entrepreneur can understand a query,
see the evidence already available, prepare a response, attach documents and
record a response submission without pretending to call a government API.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm_provider import generate_with_fallback
from app.models import (
    Approval,
    ApplicationQuery,
    ApplicationQueryStatus,
    Document,
    DocumentStatus,
    GovernmentApplication,
    Project,
    approval_documents,
)
from app.services.gateway_service import GatewayService

logger = logging.getLogger(__name__)


_EVIDENCE_RULES = [
    ("ETP capacity details", ("etp", "effluent", "treatment plant", "capacity")),
    ("Water meter reading", ("water meter", "meter reading", "water consumption")),
    ("Factory layout / site plan", ("factory layout", "site plan", "layout drawing", "layout")),
    ("Fire safety plan", ("fire safety plan", "fire plan", "fire layout")),
    ("Boiler certificate / registration", ("boiler", "steam boiler")),
    ("Pollution monitoring report", ("pollution report", "emission report", "monitoring report", "emission")),
    ("PAN / identity proof", ("pan", "permanent account number", "identity proof")),
    ("GST registration proof", ("gstin", "gst registration", "gst certificate")),
    ("Land / title / lease document", ("land", "title deed", "lease deed", "property")),
]


class QueryResolutionService:
    """Explain a government query and manage its applicant response lifecycle."""

    def __init__(self, db: AsyncSession, gateway: GatewayService | None = None):
        self.db = db
        self.gateway = gateway or GatewayService()

    async def resolve_for_approval(self, approval: Approval) -> dict:
        """Resolve the current government query and persist a local query record."""
        gov = await self._government_record(approval.id)
        query_text = None
        if gov:
            raw = gov.raw_response or {}
            query_text = (raw.get("data") or {}).get("query") or raw.get("query")

        if not query_text and gov:
            try:
                env = await self.gateway.get_status(gov.system, gov.government_application_id)
                query_text = ((env or {}).get("data") or {}).get("query")
            except Exception as exc:  # noqa: BLE001 - gateway is optional for guided/demo flows
                logger.info("Government query poll unavailable: %s", exc)

        if gov and query_text:
            raw = gov.raw_response or {}
            if raw.get("query") != query_text:
                gov.raw_response = {**raw, "query": query_text}
                await self.db.commit()

        record = await self.ensure_query_record(approval, gov, query_text)
        return await self._compose(approval, gov, record, query_text)

    async def ensure_query_record(
        self,
        approval: Approval,
        gov: GovernmentApplication | None,
        query_text: str | None,
    ) -> ApplicationQuery | None:
        if not query_text:
            return None

        fingerprint = _fingerprint(query_text)
        result = await self.db.execute(
            select(ApplicationQuery)
            .where(
                ApplicationQuery.approval_id == approval.id,
                ApplicationQuery.query_fingerprint == fingerprint,
            )
            .order_by(ApplicationQuery.created_at.desc())
        )
        record = result.scalars().first()
        if record:
            if gov and record.government_application_id != gov.government_application_id:
                record.government_application_id = gov.government_application_id
                record.system = gov.system
                await self.db.commit()
            return record

        record = ApplicationQuery(
            approval_id=approval.id,
            government_application_id=gov.government_application_id if gov else None,
            system=gov.system if gov else None,
            query_text=query_text,
            query_fingerprint=fingerprint,
            status=ApplicationQueryStatus.OPEN.value,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def save_response(self, approval: Approval, query_id: str, response_text: str, ready: bool) -> ApplicationQuery:
        record = await self._owned_record(approval, query_id)
        if record.status == ApplicationQueryStatus.SUBMITTED.value:
            raise ValueError("This query response has already been submitted and is read-only")
        cleaned = (response_text or "").strip()
        if not cleaned:
            raise ValueError("Response text is required")
        record.response_draft = cleaned
        record.status = ApplicationQueryStatus.READY.value if ready else ApplicationQueryStatus.DRAFT.value
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def submit_response(self, approval: Approval, query_id: str, response_text: str | None = None) -> dict:
        record = await self._owned_record(approval, query_id)
        if record.status == ApplicationQueryStatus.SUBMITTED.value:
            return self._response_payload(record, external_action="ALREADY_RECORDED")
        cleaned = (response_text or record.response_draft or "").strip()
        if not cleaned:
            raise ValueError("Add a response before submitting")

        record.response_draft = cleaned
        record.submitted_response = cleaned
        record.submitted_at = datetime.utcnow()
        record.status = ApplicationQueryStatus.SUBMITTED.value

        # Important: no government API is called here. The response is recorded
        # locally and the applicant is told whether the journey is demo/guided.
        from app.services.approval_workflow import ApprovalWorkflowEngine

        approval_status = approval.status.value if hasattr(approval.status, "value") else str(approval.status)
        if approval_status == "QUERY_RAISED":
            decision = ApprovalWorkflowEngine("ENTREPRENEUR").apply(approval, "SUBMITTED")
            if not decision.allowed:
                raise ValueError(decision.error or "Application cannot be resubmitted from its current status")
        await self.db.commit()
        await self.db.refresh(record)

        try:
            from app.audit.logging import log_audit
            await log_audit(
                self.db,
                user_id=str(await self._project_owner_id(approval)),
                action="application.query_response_submitted",
                resource_type="application_query",
                resource_id=str(record.id),
                details={
                    "approval_id": str(approval.id),
                    "query_id": str(record.id),
                    "government_application_id": record.government_application_id,
                    "external_submission": False,
                },
            )
        except Exception as exc:  # noqa: BLE001 - audit is a side-channel
            logger.warning("Query response audit failed: %s", exc)

        try:
            from app.notifications.service import NotificationService
            owner_id = await self._project_owner_id(approval)
            await NotificationService(self.db).create(
                str(owner_id),
                "Query Response Recorded",
                f"Your response for {approval.name} has been recorded in UdyogSetu and the application moved back to submitted review.",
                category="query",
                severity="info",
                project_id=approval.project_id,
                reference_id=str(approval.id),
            )
        except Exception as exc:  # noqa: BLE001 - notification is a side-channel
            logger.warning("Query response notification failed: %s", exc)

        return self._response_payload(record, external_action="RECORDED_LOCALLY")

    async def _compose(
        self,
        approval: Approval,
        gov: GovernmentApplication | None,
        record: ApplicationQuery | None,
        query_text: str | None,
    ) -> dict:
        if not query_text or not record:
            return {
                "query_present": False,
                "status": None,
                "query_id": None,
                "explanation": "No open query for this application.",
                "required_evidence": [],
                "relevant_documents": [],
                "available_documents": [],
                "regulatory_context": [],
                "suggestion": None,
                "suggested_response": None,
                "response_draft": None,
                "can_save": False,
                "can_submit": False,
                "project_id": str(approval.project_id),
                "government": self._government_payload(gov),
            }

        docs_result = await self.db.execute(
            select(Document).where(Document.project_id == approval.project_id)
        )
        docs = list(docs_result.scalars().all())
        attached_result = await self.db.execute(
            select(Document)
            .join(approval_documents, approval_documents.c.document_id == Document.id)
            .where(approval_documents.c.approval_id == approval.id)
        )
        attached_documents = list(attached_result.scalars().all())
        attached_ids = {str(d.id) for d in attached_documents}

        evidence = self._required_evidence(query_text, docs)
        relevant_documents = self._relevant_documents(query_text, docs)
        available_documents = [
            self._document_payload(d, attached=str(d.id) in attached_ids)
            for d in docs
        ]

        regulatory_context: list = []
        try:
            from app.services.rag_service import RAGService
            rag = await RAGService(self.db).answer_regulatory_question(query_text)
            regulatory_context = rag.get("sources", [])[:3]
        except Exception as exc:  # noqa: BLE001 - RAG should never block query handling
            logger.info("RAG context unavailable for query: %s", exc)

        start = time.perf_counter()
        explanation = await self._ai_text(
            system="You are UdyogSetu. Explain a government query to an entrepreneur in plain language. Do not invent requirements.",
            prompt=(
                f"Government query: {query_text}\n"
                f"Requested evidence identified from the literal query: {', '.join(item['label'] for item in evidence) or 'No specific evidence label identified'}\n"
                "Explain what the department is asking for in plain language. Mention only what is supported by the query. Keep it under 80 words."
            ),
        )
        suggested_response = await self._ai_text(
            system="You are UdyogSetu. Draft a factual applicant response to a government query. Never invent facts or legal claims.",
            prompt=(
                f"Query: {query_text}\n"
                f"Evidence available in the applicant workspace: {', '.join(d['file_name'] for d in relevant_documents) or 'None identified'}\n"
                "Draft a concise response that refers only to the query and the listed available documents. Do not claim that a response was sent to a government system. Keep under 120 words."
            ),
        )
        logger.debug("Query center AI composition completed in %sms", int((time.perf_counter() - start) * 1000))

        attached = [self._document_payload(d, attached=True) for d in attached_documents]
        status = record.status or ApplicationQueryStatus.OPEN.value
        return {
            "query_present": True,
            "project_id": str(approval.project_id),
            "query_id": str(record.id),
            "status": status,
            "query": query_text,
            "explanation": explanation,
            "required_evidence": evidence,
            "relevant_documents": relevant_documents,
            "available_documents": available_documents,
            "attached_documents": attached,
            "regulatory_context": regulatory_context,
            "suggestion": suggested_response,
            "suggested_response": suggested_response,
            "response_draft": record.response_draft,
            "submitted_response": record.submitted_response,
            "submitted_at": record.submitted_at.isoformat() if record.submitted_at else None,
            "can_save": status != ApplicationQueryStatus.SUBMITTED.value,
            "can_submit": status != ApplicationQueryStatus.SUBMITTED.value,
            "government": self._government_payload(gov),
            "disclaimer": "AI assistance is advisory. Response submission to the external authority is not performed by UdyogSetu without an authorized integration.",
        }

    async def _ai_text(self, system: str, prompt: str) -> str:
        try:
            return await generate_with_fallback(system, prompt, temperature=0.2, max_tokens=300)
        except Exception as exc:  # noqa: BLE001 - deterministic fallback keeps the center usable
            logger.info("AI query composition unavailable: %s", exc)
            return _safe_fallback(prompt)

    async def _government_record(self, approval_id):
        result = await self.db.execute(
            select(GovernmentApplication).where(GovernmentApplication.approval_id == approval_id)
        )
        return result.scalar_one_or_none()

    async def _owned_record(self, approval: Approval, query_id: str) -> ApplicationQuery:
        try:
            record_uuid = UUID(str(query_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("Invalid query id") from exc
        result = await self.db.execute(
            select(ApplicationQuery).where(
                ApplicationQuery.id == record_uuid,
                ApplicationQuery.approval_id == approval.id,
            )
        )
        record = result.scalar_one_or_none()
        if not record:
            raise ValueError("Query not found")
        return record

    async def _project_owner_id(self, approval: Approval):
        result = await self.db.execute(select(Project).where(Project.id == approval.project_id))
        project = result.scalar_one_or_none()
        return project.user_id if project else None

    @staticmethod
    def _government_payload(gov: GovernmentApplication | None) -> dict:
        if not gov:
            return {"system": None, "government_application_id": None, "source": "not_connected"}
        return {
            "system": gov.system,
            "government_application_id": gov.government_application_id,
            "source": "prototype_simulator" if gov.system else "not_connected",
        }

    @staticmethod
    def _response_payload(record: ApplicationQuery, external_action: str) -> dict:
        return {
            "query_id": str(record.id),
            "status": record.status,
            "response_draft": record.response_draft,
            "submitted_at": record.submitted_at.isoformat() if record.submitted_at else None,
            "external_submission": False,
            "external_action": external_action,
            "message": "Response recorded in UdyogSetu. No external government API was called.",
        }

    @staticmethod
    def _document_payload(document: Document, attached: bool) -> dict:
        status = document.status.value if hasattr(document.status, "value") else str(document.status)
        return {
            "document_id": str(document.id),
            "file_name": document.file_name,
            "document_type": (document.custom_metadata or {}).get("document_type"),
            "status": status,
            "validation_errors": document.validation_errors or [],
            "attached": attached,
        }

    def _relevant_documents(self, query_text: str, docs: list[Document]) -> list[dict]:
        query_tokens = _tokens(query_text)
        results = []
        for d in docs:
            raw = d.custom_metadata or {}
            haystack_text = " ".join(
                [d.file_name or "", raw.get("document_type") or "", d.extracted_text or "", str(d.extracted_fields or "")]
            )
            haystack = _tokens(haystack_text)
            overlap = len(query_tokens & haystack)
            phrase_boost = self._phrase_boost(query_text, haystack_text)
            score = overlap + phrase_boost
            if score > 0:
                results.append((score, self._document_payload(d, attached=False)))
        results.sort(key=lambda item: (-item[0], item[1]["file_name"].lower()))
        return [item[1] | {"match_score": item[0]} for item in results[:8]]

    def _required_evidence(self, query_text: str, docs: list[Document]) -> list[dict]:
        lowered = query_text.lower()
        items = []
        for label, needles in _EVIDENCE_RULES:
            if any(needle in lowered for needle in needles):
                matches = []
                for doc in docs:
                    searchable = " ".join([
                        doc.file_name or "",
                        (doc.custom_metadata or {}).get("document_type") or "",
                        doc.extracted_text or "",
                        str(doc.extracted_fields or {}),
                    ]).lower()
                    if any(needle in searchable for needle in needles):
                        matches.append(self._document_payload(doc, attached=False))
                items.append({
                    "label": label,
                    "satisfied": bool(matches),
                    "matched_documents": matches[:5],
                })
        if not items:
            items.append({
                "label": "Supporting evidence explicitly requested in the query",
                "satisfied": bool(docs),
                "matched_documents": self._relevant_documents(query_text, docs)[:5],
            })
        return items

    @staticmethod
    def _phrase_boost(query_text: str, haystack_text: str) -> int:
        qt = query_text.lower()
        ht = haystack_text.lower()
        phrases = ["etp capacity", "water meter", "factory layout", "fire safety", "boiler registration", "gstin", "pan"]
        return sum(3 for phrase in phrases if phrase in qt and phrase in ht)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def _fingerprint(text: str) -> str:
    import hashlib
    normalized = " ".join((text or "").split()).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:64]


def _safe_fallback(prompt: str) -> str:
    # Return a constrained, non-hallucinatory fallback based on the request itself.
    match = re.search(r"(?:Government query|Query):\s*(.+?)(?:\n|$)", prompt, re.IGNORECASE)
    query = match.group(1).strip() if match else "the department's query"
    return f"Please review the department query: {query}. Provide only the supporting information and documents specifically requested by the department."
