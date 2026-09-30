"""Step-20 final SIH demo hardening regression tests."""

import asyncio

import pytest

from app.integrations.government_adapters import GovernmentAPIGateway
from app.integrations.mock_gov_api import MockGovAPI
from app.services.demo_readiness import DemoReadinessService


def test_prototype_submission_ids_are_deterministic():
    gateway = GovernmentAPIGateway(provider="prototype")

    async def run():
        first = await gateway.submit_application("mpcb", {"application_key": "approval-123", "sla_days": 60})
        second = await gateway.submit_application("mpcb", {"application_key": "approval-123", "sla_days": 60})
        assert first["application_id"] == second["application_id"]

    asyncio.run(run())


def test_si_demo_status_story_is_deterministic():
    gateway = GovernmentAPIGateway(provider="prototype")

    expected = {
        "maitri": "UNDER_REVIEW",
        "mpcb": "QUERY_RAISED",
        "midc": "APPROVED",
        "boiler": "UNDER_REVIEW",
        "fire": "APPROVED",
        "labour": "APPROVED",
    }

    async def run():
        for system, expected_status in expected.items():
            first = await gateway.get_application_status(system, f"{system.upper()}-DEMO-001")
            second = await gateway.get_application_status(system, f"{system.upper()}-DEMO-001")
            assert first["status"] == expected_status
            assert second["status"] == expected_status

    asyncio.run(run())


def test_mock_verification_score_is_deterministic():
    mock = MockGovAPI()

    async def run():
        first = await mock.check_scheme_eligibility("PSI", {"sector": "Textile", "investment": 350000000})
        second = await mock.check_scheme_eligibility("PSI", {"sector": "Textile", "investment": 350000000})
        assert first["data"]["eligibility_score"] == second["data"]["eligibility_score"]
        assert first["data"]["eligible"] == second["data"]["eligible"]

    asyncio.run(run())


@pytest.mark.asyncio
async def test_demo_readiness_reports_missing_seed_without_mutation(db_session):
    from uuid import UUID
    result = await DemoReadinessService(db_session).inspect(UUID("00000000-0000-0000-0000-000000000001"))
    assert result["ready"] is False
    assert result["project_id"] is None
    assert result["integration_provider"] == "prototype"
    assert result["total"] == len(result["checks"])
    assert all({"key", "label", "ok", "detail", "href"}.issubset(check) for check in result["checks"])
