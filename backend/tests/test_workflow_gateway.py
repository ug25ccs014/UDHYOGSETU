"""Tests for the copilot query-detection workflow and gateway layer."""

import pytest

from app.integrations.mock_gov_api import MockGovAPI
from app.services.gateway_service import GatewayService
from app.workflows.copilot_workflow import CopilotWorkflow


def test_intent_detection_routes_regulation():
    wf = CopilotWorkflow(None)
    assert wf.detect_intent("What regulation applies to my boiler?") == "regulation"
    assert wf.detect_intent("Where is my application status?") == "status"
    assert wf.detect_intent("What if i salute?") == "general"


def test_mock_gov_verify_gstin():
    import asyncio
    mock = MockGovAPI()
    result = asyncio.run(mock.verify_gstin("27ABCDE1234F1Z5"))
    data = result["data"]
    assert data["valid"] is True
    assert result["meta"]["system"] == "gst"
    assert result["meta"]["request_id"]


def test_mock_gov_services_envelope():
    import asyncio
    mock = MockGovAPI()
    services = asyncio.run(mock.list_services("mpcb"))
    names = [s["name"] for s in services["data"]]
    assert "Consent to Establish" in names


@pytest.mark.asyncio
async def test_gateway_health_snapshot():
    svc = GatewayService()
    health = await svc.system_health(force=True)
    assert "systems" in health
    assert isinstance(health["systems"], dict)


@pytest.mark.asyncio
async def test_gateway_unknown_system_returns_unavailable():
    svc = GatewayService()
    result = await svc.get_status("unknown_system", "APP-1")
    # _with_retry should surface an error status rather than raise.
    assert "error" in result or "status" in result
