"""Explore Government Services — catalog discovery, applicability, checklist.

Implements the Explore module on top of the existing domain objects:

  * the catalog lives in the ``government_services`` table (seeded idempotently
    from ``data/services/explore_services.json`` at startup),
  * project applicability is computed by the existing ``ApprovalEngine`` against
    the ``ApprovalRule`` a service points at (no second rules engine),
  * a saved application IS an ``Approval`` row in ``NOT_STARTED`` state, so the
    whole lifecycle (submit, track, SLA, officer review, audit, notifications)
    reuses the existing application system unchanged.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.logging import log_audit
from app.models import (
    Approval,
    ApprovalRule,
    ApprovalStatus,
    Document,
    GovernmentService,
    Project,
)
from app.rules.approval_engine import ApprovalEngine

logger = logging.getLogger(__name__)

# Prefix stored on the Approval.source so checklist-created applications can be
# told apart from roadmap rows produced by /projects/{id}/analyze.
CHECKLIST_SOURCE_PREFIX = "explore:"


class ExploreService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Catalog
    # ------------------------------------------------------------------
    async def list_services(
        self,
        q: str | None = None,
        category: str | None = None,
        authority: str | None = None,
        application_mode: str | None = None,
        service_type: str | None = None,
        limit: int = 100,
    ) -> list[GovernmentService]:
        stmt = select(GovernmentService).where(GovernmentService.is_active.is_(True))

        if category:
            stmt = stmt.where(GovernmentService.category == category)
        if authority:
            stmt = stmt.where(GovernmentService.authority.contains(authority))
        if application_mode:
            stmt = stmt.where(GovernmentService.application_mode == application_mode.upper())
        if service_type:
            stmt = stmt.where(GovernmentService.service_type == service_type.upper())
        if q:
            lowered = f"%{q.strip().lower()}%"
            stmt = stmt.where(
                GovernmentService.name.ilike(lowered)
                | GovernmentService.description.ilike(lowered)
                | GovernmentService.official_reference.ilike(lowered)
                | GovernmentService.category.ilike(lowered)
            )

        stmt = stmt.order_by(GovernmentService.category, GovernmentService.name).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_categories(self) -> list[str]:
        result = await self.db.execute(
            select(GovernmentService.category)
            .where(GovernmentService.is_active.is_(True))
            .order_by(GovernmentService.category)
            .distinct()
        )
        return [row[0] for row in result.all() if row[0]]

    async def get_service(self, identifier: str) -> GovernmentService | None:
        result = await self.db.execute(
            select(GovernmentService).where(GovernmentService.slug == identifier)
        )
        service = result.scalar_one_or_none()
        if service:
            return service
        try:
            result = await self.db.execute(
                select(GovernmentService).where(GovernmentService.id == UUID(identifier))
            )
            return result.scalar_one_or_none()
        except (ValueError, AttributeError, TypeError):
            return None

    async def get_rule(self, service: GovernmentService) -> ApprovalRule | None:
        if not service.approval_rule_id:
            return None
        return await self.db.get(ApprovalRule, service.approval_rule_id)

    async def find_service_for_approval(self, approval: Approval) -> GovernmentService | None:
        """Resolve the catalog service that created a checklist Approval, if any."""
        source = approval.source or ""
        if not source.startswith(CHECKLIST_SOURCE_PREFIX):
            return None
        slug = source[len(CHECKLIST_SOURCE_PREFIX):]
        return await self.get_service(slug)

    # ------------------------------------------------------------------
    # Applicability
    # ------------------------------------------------------------------
    async def check_applicability(self, service: GovernmentService, project: Project) -> dict:
        """Evaluate whether a service applies to a project using the existing
        rule engine. Returns an explicit NOT_DETERMINED when no rule is linked
        (we will not fabricate a determination)."""
        rule = await self.get_rule(service)
        if rule is None:
            return {
                "service_id": str(service.id),
                "service_slug": service.slug,
                "status": "NOT_DETERMINED",
                "reason": "No deterministic applicability rule is linked to this service. Review the eligibility criteria before applying.",
                "matched_conditions": [],
                "failed_conditions": [],
                "required_documents": [d.get("document_type") or d.get("description") or "" for d in (service.applicable_documents or [])],
                "rule_id": None,
            }

        details = ApprovalEngine(self.db).evaluate_rule_details(rule, project)
        status = "APPLICABLE" if details["applies"] else "NOT_APPLICABLE"
        required = list(rule.required_documents or [])
        for entry in (service.applicable_documents or []):
            label = entry.get("document_type") or entry.get("description")
            if label and label not in required:
                required.append(label)

        return {
            "service_id": str(service.id),
            "service_slug": service.slug,
            "status": status,
            "reason": (
                "This service applies to your project based on the matching conditions below."
                if details["applies"]
                else "Based on your project profile this service is currently not applicable."
            ),
            "matched_conditions": details["matched"],
            "failed_conditions": details["failed"],
            "required_documents": required,
            "rule_id": str(rule.id),
        }

    # ------------------------------------------------------------------
    # Checklist (an Approval in NOT_STARTED/DRAFT state)
    # ------------------------------------------------------------------
    async def add_to_checklist(
        self,
        service: GovernmentService,
        project_id: UUID,
        user_id: str,
    ) -> tuple[Approval, bool]:
        """Create (or return the existing) checklist application for a service."""
        result = await self.db.execute(
            select(Approval).where(
                Approval.project_id == project_id,
                Approval.name == service.name,
                Approval.source == f"{CHECKLIST_SOURCE_PREFIX}{service.slug}",
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing, False

        approval = Approval(
            project_id=project_id,
            name=service.name,
            department=service.department,
            is_mandatory=False,
            risk_level=service.risk_level or "MEDIUM",
            estimated_processing_days=service.sla_days,
            renewal_period_days=service.renewal_period_days,
            status=ApprovalStatus.NOT_STARTED,
            source=f"{CHECKLIST_SOURCE_PREFIX}{service.slug}",
        )
        self.db.add(approval)
        await self.db.commit()
        await self.db.refresh(approval)

        try:
            await log_audit(
                self.db,
                user_id=user_id,
                action="explore.checklist_add",
                resource_type="approval",
                resource_id=str(approval.id),
                details={"service": service.slug, "project_id": str(project_id)},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Audit failed for checklist add: %s", exc)
            await self.db.rollback()

        return approval, True

    async def start_application(self, approval: Approval, actor_role: str = "ENTREPRENEUR") -> dict:
        """Start a checklisted application (NOT_STARTED -> DRAFT)."""
        from app.services.approval_workflow import ApprovalWorkflowEngine

        engine = ApprovalWorkflowEngine(actor_role)
        target = ApprovalStatus.DRAFT
        decision = engine.apply(approval, target)
        await self.db.commit()
        await self.db.refresh(approval)
        return {
            "allowed": decision.allowed,
            "error": decision.error,
            "application_id": approval.application_id or str(approval.id),
            "status": approval.status.value if hasattr(approval.status, "value") else str(approval.status),
        }

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------
    async def attach_document(self, approval: Approval, document: Document) -> dict:
        await self.db.refresh(approval, ["documents"])
        if not any(str(d.id) == str(document.id) for d in approval.documents):
            approval.documents.append(document)
            await self.db.commit()
        return {"document_id": str(document.id), "application_id": approval.application_id or str(approval.id), "attached": True}

    async def detach_document(self, approval: Approval, document_id: UUID) -> dict:
        await self.db.refresh(approval, ["documents"])
        remaining = [d for d in approval.documents if str(d.id) != str(document_id)]
        if len(remaining) != len(approval.documents):
            approval.documents = remaining
            await self.db.commit()
        return {"document_id": str(document_id), "application_id": approval.application_id or str(approval.id), "attached": False}

    async def checklist_requirements(self, approval: Approval) -> dict:
        """Requirements + current linked documents + possible transitions."""
        service = None
        source = approval.source or ""
        if source.startswith(CHECKLIST_SOURCE_PREFIX):
            slug = source[len(CHECKLIST_SOURCE_PREFIX):]
            service = await self.get_service(slug)

        required: list[dict] = []
        if service:
            for entry in service.applicable_documents or []:
                if isinstance(entry, str):
                    required.append({"document_type": entry, "description": entry, "required": True})
                else:
                    required.append(
                        {
                            "document_type": entry.get("document_type") or entry.get("description") or "Document",
                            "description": entry.get("description") or entry.get("document_type") or "",
                            "required": entry.get("required", True),
                        }
                    )

        from app.services.approval_workflow import ApprovalWorkflowEngine

        engine = ApprovalWorkflowEngine("ENTREPRENEUR")
        status = approval.status.value if hasattr(approval.status, "value") else str(approval.status)
        await self.db.refresh(approval, ["documents"])
        return {
            "approval_id": str(approval.id),
            "application_id": approval.application_id or str(approval.id),
            "name": approval.name,
            "department": approval.department,
            "status": status,
            "service_slug": service.slug if service else None,
            "required_documents": required,
            "attached_documents": [
                {
                    "id": str(d.id),
                    "file_name": d.file_name,
                    "status": d.status.value if hasattr(d.status, "value") else str(d.status),
                    "document_type": (d.custom_metadata or {}).get("document_type"),
                }
                for d in approval.documents
            ],
            "available_transitions": engine.list_possible_transitions(approval.status),
        }