"""Tests for the controlled AI tool calling (spec §11)."""

import uuid

import pytest

from app.ai.tools import ToolCallingError, ToolCallingService, ToolRegistry
from app.core.database import AsyncSessionLocal
from app.models import Approval, Project
from app.services.copilot_tools import get_copilot_tools

USER_UUID = uuid.UUID("11111111-1111-1111-1111-111111111111")


async def _make_project(db, user_id=USER_UUID):
    project = Project(
        user_id=user_id,
        name="Demo Textiles",
        company_name="ABC Textiles Pvt Ltd",
        industry="Textile",
        sector="Textile",
        investment_amount=20000000,
        employees=50,
        location_state="Maharashtra",
    )
    db.add(project)
    await db.flush()
    await db.commit()
    return project


def test_registry_rejects_unknown_tool():
    registry = ToolRegistry()
    with pytest.raises(ToolCallingError):
        registry.get("does_not_exist")


def test_registry_lists_tools():
    registry = get_copilot_tools()
    names = {t["name"] for t in registry.list()}
    assert {"get_project_profile", "get_approval_status", "search_documents",
            "check_compliance", "find_incentives"} <= names


async def test_tool_calling_returns_project_profile():
    async with AsyncSessionLocal() as db:
        project = await _make_project(db)
        registry = get_copilot_tools()
        service = ToolCallingService(registry, db)
        outcome = await service.execute(
            "get_project_profile",
            {"project_id": str(project.id)},
        )
        assert outcome["ok"] is True
        assert outcome["result"]["project"]["company_name"] == "ABC Textiles Pvt Ltd"


async def test_tool_calling_validates_missing_required_arg():
    registry = get_copilot_tools()
    service = ToolCallingService(registry, None)
    outcome = await service.execute("get_project_profile", {})
    assert outcome["ok"] is False
    assert "Missing required" in outcome["error"]


async def test_approval_status_tool():
    async with AsyncSessionLocal() as db:
        project = await _make_project(db)
        db.add(Approval(project_id=project.id, name="MPCB CtE", department="MPCB", status="SUBMITTED"))
        await db.commit()
        registry = get_copilot_tools()
        service = ToolCallingService(registry, db)
        outcome = await service.execute(
            "get_approval_status",
            {"project_id": str(project.id)},
        )
        assert outcome["ok"] is True
        assert outcome["result"]["approvals"][0]["name"] == "MPCB CtE"
