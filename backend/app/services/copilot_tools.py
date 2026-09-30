"""Concrete controlled tools the copilot can invoke (spec §11).

The tools wrap existing services so the LLM can pull real data on demand:
  * get_project_profile   - the business details used for approvals
  * get_approval_status   - current status/SLA of a project's applications
  * search_documents      - the extracted fields/type of uploaded documents
  * check_compliance      - compliance item status for the project
  * find_incentives       - matched subsidies for the project

These are the only capabilities exposed to the model; it cannot run arbitrary
code or write to the store.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.ai.tools import Tool, ToolRegistry
from app.models import Approval, ComplianceItem, Document, Project


def _project(obj) -> dict:
    return {
        "id": str(obj.id),
        "name": obj.name,
        "company_name": obj.company_name,
        "industry": obj.industry,
        "sector": obj.sector,
        "project_stage": obj.project_stage,
        "investment_amount": obj.investment_amount,
        "employees": obj.employees,
        "location_state": obj.location_state,
        "location_district": obj.location_district,
        "location_city": obj.location_city,
        "pollution_potential": obj.pollution_potential,
        "has_boiler": obj.has_boiler,
        "hazardous_materials": obj.hazardous_materials,
    }


async def _get_project_profile(db, args: dict) -> dict:
    result = await db.execute(select(Project).where(Project.id == UUID(str(args["project_id"]))))
    project = result.scalar_one_or_none()
    if not project:
        return {"error": "Project not found"}
    return {"project": _project(project)}


async def _get_approval_status(db, args: dict) -> dict:
    result = await db.execute(
        select(Approval).where(Approval.project_id == UUID(str(args["project_id"])))
    )
    approvals = result.scalars().all()
    return {
        "approvals": [
            {
                "name": a.name,
                "department": a.department,
                "status": a.status.value if hasattr(a.status, "value") else str(a.status),
                "estimated_processing_days": a.estimated_processing_days,
                "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
            }
            for a in approvals
        ]
    }


async def _search_documents(db, args: dict) -> dict:
    query = str(args.get("query", "")).lower()
    result = await db.execute(
        select(Document).where(Document.project_id == UUID(str(args["project_id"])))
    )
    docs = result.scalars().all()
    matches = []
    for d in docs:
        haystack = " ".join([
            d.file_name or "",
            (d.custom_metadata or {}).get("document_type") or "",
            " ".join((d.extracted_fields or {}).keys()),
        ]).lower()
        if query and query not in haystack:
            continue
        matches.append({
            "id": str(d.id),
            "file_name": d.file_name,
            "document_type": (d.custom_metadata or {}).get("document_type"),
            "status": d.status.value if hasattr(d.status, "value") else str(d.status),
            "extracted_fields": (d.extracted_fields or {}) if args.get("include_fields") else None,
            "validation_errors": d.validation_errors or [],
        })
    return {"documents": matches}


async def _check_compliance(db, args: dict) -> dict:
    result = await db.execute(
        select(ComplianceItem).where(ComplianceItem.project_id == UUID(str(args["project_id"])))
    )
    items = result.scalars().all()
    return {
        "compliance_items": [
            {
                "category": c.category,
                "requirement": c.requirement,
                "frequency": c.frequency,
                "status": c.status.value if hasattr(c.status, "value") else str(c.status),
                "due_date": c.due_date.isoformat() if c.due_date else None,
            }
            for c in items
        ]
    }


async def _find_incentives(db, args: dict) -> dict:
    from app.services.incentive_matcher import IncentiveMatcher
    result = await db.execute(select(Project).where(Project.id == UUID(str(args["project_id"]))))
    project = result.scalar_one_or_none()
    if not project:
        return {"error": "Project not found"}
    profile = {
        "sector": project.sector,
        "location": project.location_state,
        "investment_amount": project.investment_amount,
        "employee_count": project.employees,
    }
    matches = await IncentiveMatcher(db).find_matching_schemes(
        {k: v for k, v in profile.items() if v is not None}
    )
    return {"matches": matches}


def build_copilot_tools() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(Tool(
        "get_project_profile",
        "Get the business profile (industry, sector, investment, location, boiler, hazardous) for a project.",
        {
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": ["project_id"],
        },
        _get_project_profile,
    ))
    registry.register(Tool(
        "get_approval_status",
        "Get the current application/approval status summary for a project.",
        {
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": ["project_id"],
        },
        _get_approval_status,
    ))
    registry.register(Tool(
        "search_documents",
        "Search uploaded documents for a project by type/name and return extracted fields and validation errors.",
        {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "query": {"type": "string"},
                "include_fields": {"type": "boolean", "default": False},
            },
            "required": ["project_id"],
        },
        _search_documents,
    ))
    registry.register(Tool(
        "check_compliance",
        "Get compliance items and their status (on track / at risk / overdue) for a project.",
        {
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": ["project_id"],
        },
        _check_compliance,
    ))
    registry.register(Tool(
        "find_incentives",
        "Find government subsidy/incentive schemes a project qualifies for.",
        {
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": ["project_id"],
        },
        _find_incentives,
    ))
    return registry


_tools_registry: ToolRegistry | None = None


def get_copilot_tools() -> ToolRegistry:
    global _tools_registry
    if _tools_registry is None:
        _tools_registry = build_copilot_tools()
    return _tools_registry
