"""Knowledge graph builder (spec §31).

Exposes the entity/relationship model of the platform as a graph using the
existing PostgreSQL relations (no Neo4j needed for the MVP). Entities include
Project, Approval, Department, Document, Regulation, Compliance and Scheme.

Relationship types follow the spec:
    PROJECT_REQUIRES_APPROVAL
    APPROVAL_DEPENDS_ON
    APPROVAL_REQUIRES_DOCUMENT
    APPROVAL_ISSUED_BY
    APPROVAL_HAS_COMPLIANCE
    REGULATION_GOVERNS_APPROVAL
    PROJECT_ELIGIBLE_FOR_SCHEME
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.models import (
    Approval,
    ApprovalRule,
    ComplianceItem,
    Document,
    KnowledgeDocument,
    Project,
)
from app.services.incentive_matcher import IncentiveMatcher


class KnowledgeGraphService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def build_graph(self, project_id: UUID) -> dict:
        project = (await self.db.execute(
            select(Project).where(Project.id == project_id)
        )).scalar_one_or_none()
        if not project:
            return {"nodes": [], "relationships": [], "stats": {}}

        nodes: list[dict] = []
        relationships: list[dict] = []

        self._add_node(nodes, "project", str(project.id), project.name, "Project")

        approvals = (await self.db.execute(
            select(Approval).where(Approval.project_id == project_id)
        )).scalars().all()

        documents = list((await self.db.execute(
            select(Document).where(Document.project_id == project_id)
        )).scalars().all())

        compliance = list((await self.db.execute(
            select(ComplianceItem).where(ComplianceItem.project_id == project_id)
        )).scalars().all())

        # Regulation / source nodes referenced by approvals.
        for approval in approvals:
            node_id = f"approval:{approval.id}"
            self._add_node(
                nodes, "entity", node_id, approval.name,
                f"Approval ({approval.department})",
                {"status": approval.status.value if hasattr(approval.status, "value") else str(approval.status)},
            )
            relationships.append({
                "source": "project", "target": node_id, "type": "PROJECT_REQUIRES_APPROVAL",
            })

            # ISSUED_BY department.
            dept_id = f"dept:{approval.department or 'unknown'}"
            self._add_node(nodes, "entity", dept_id, approval.department or "Unknown", "Department")
            relationships.append({
                "source": node_id, "target": dept_id, "type": "APPROVAL_ISSUED_BY",
            })

            # DEPENDS_ON other approvals, derived from the matching approval rule.
            rule = (await self.db.execute(
                select(ApprovalRule).where(
                    ApprovalRule.department == approval.department,
                    ApprovalRule.sector == approval.sector,
                    ApprovalRule.is_active.is_(True),
                ).limit(1)
            )).scalar_one_or_none()
            for dep in (rule.dependencies if rule else []) or []:
                dep_id = f"dep:{dep}"
                self._add_node(nodes, "entity", dep_id, dep, "Approval")
                relationships.append({
                    "source": node_id, "target": dep_id, "type": "APPROVAL_DEPENDS_ON",
                })

            # REGULATION_GOVERNS_APPROVAL: authoritative regulation by department.
            reg = (await self.db.execute(
                select(KnowledgeDocument).where(
                    KnowledgeDocument.department == approval.department,
                    KnowledgeDocument.is_latest.is_(True),
                ).limit(1)
            )).scalar_one_or_none()
            if reg:
                reg_id = f"reg:{reg.id}"
                self._add_node(nodes, "entity", reg_id, reg.title, "Regulation", {"version": reg.version})
                relationships.append({
                    "source": reg_id, "target": node_id, "type": "REGULATION_GOVERNS_APPROVAL",
                })

            # APPROVAL_REQUIRES_DOCUMENT: link uploaded documents on the same project
            # plus required documents named by the rule.
            for doc in documents:
                doc_id = f"doc:{doc.id}"
                self._add_node(nodes, "entity", doc_id, doc.file_name, "Document")
                relationships.append({
                    "source": node_id, "target": doc_id, "type": "APPROVAL_REQUIRES_DOCUMENT",
                })

        # APPROVAL_HAS_COMPLIANCE (by category/requirement matching the department).
        for item in compliance:
            comp_id = f"comp:{item.id}"
            self._add_node(nodes, "entity", comp_id, item.requirement, f"Compliance ({item.category})")
            target = f"approval:{approval_for_compliance(approvals, item)}" if approvals else None
            if target:
                relationships.append({
                    "source": target, "target": comp_id, "type": "APPROVAL_HAS_COMPLIANCE",
                })

        # PROJECT_ELIGIBLE_FOR_SCHEME.
        try:
            schemes = await IncentiveMatcher(self.db).find_matching_schemes({
                "industry": project.industry,
                "sector": project.sector,
                "location": project.location_district,
                "investment_amount": project.investment_amount,
                "employees": project.employees,
            })
            for scheme in schemes:
                scheme_id = f"scheme:{scheme['id']}"
                self._add_node(nodes, "entity", scheme_id, scheme["name"], "Scheme", {
                    "match_score": scheme.get("match_score"),
                })
                relationships.append({
                    "source": "project", "target": scheme_id, "type": "PROJECT_ELIGIBLE_FOR_SCHEME",
                })
        except Exception as exc:  # noqa: BLE001 - scheme enrichment is best-effort
            logger.debug("Scheme matching skipped for knowledge graph: %s", exc)

        stats = {
            "total_nodes": len(nodes),
            "total_relationships": len(relationships),
            "approvals": len(approvals),
            "documents": len(documents),
            "compliance_items": len(compliance),
        }
        return {"nodes": nodes, "relationships": relationships, "stats": stats}

    @staticmethod
    def _add_node(nodes, kind, node_id, label, node_type, extra=None):
        for n in nodes:
            if n["id"] == node_id:
                return
        node = {"id": node_id, "kind": kind, "label": label, "type": node_type}
        if extra:
            node.update(extra)
        nodes.append(node)


def approval_for_compliance(approvals, item) -> str | None:
    """Best-effort link a compliance item to a department-related approval."""
    category = (item.category or "").lower()
    for approval in approvals:
        if category in (approval.department or "").lower():
            return f"approval:{approval.id}"
    return str(approvals[0].id) if approvals else None
