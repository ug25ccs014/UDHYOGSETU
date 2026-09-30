"""Tests for Step 17 government-integration transparency and provider seams."""

import asyncio
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token, hash_password
from app.models import User, UserRole
from app.integrations.government_adapters import GovernmentAPIGateway
from app.services.gateway_service import GatewayService
from app.services.integration_transparency import service_integration
from app.main import app

client = TestClient(app)
PASSWORD = "Password@123"


def _email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


def _auth(role: str = "ENTREPRENEUR") -> dict:
    email = _email(role.lower())

    if role == "ENTREPRENEUR":
        payload = {"email": email, "name": "Integration Tester", "phone": "9876543210", "password": PASSWORD, "role": role}
        created = client.post("/api/auth/register", json=payload)
        assert created.status_code == 201, created.text
    else:
        async def _provision():
            async with AsyncSessionLocal() as db:
                user = User(
                    email=email,
                    name="Integration Officer",
                    phone="9876543210",
                    password_hash=hash_password(PASSWORD),
                    role=UserRole.OFFICER,
                    is_active=True,
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
                return user
        asyncio.run(_provision())

    logged = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert logged.status_code == 200, logged.text
    return {"Authorization": f"Bearer {logged.json()['access_token']}"}


def test_gateway_catalog_marks_prototype_and_future_authorized_systems():
    gateway = GovernmentAPIGateway(provider="prototype")
    catalog = gateway.catalog()
    maitri = next(item for item in catalog if item["system"] == "maitri")
    gst = next(item for item in catalog if item["system"] == "gst")

    assert maitri["classification"] == "PROTOTYPE_SIMULATOR"
    assert maitri["is_simulated"] is True
    assert maitri["supports_submission"] is True
    assert gst["classification"] == "EXTERNAL_PORTAL"
    assert gst["status"] == "PORTAL_AVAILABLE"


def test_authorized_provider_requires_explicit_adapter_injection():
    gateway = GovernmentAPIGateway(provider="authorized")
    descriptor = gateway.descriptor("mpcb")
    assert descriptor["classification"] == "FUTURE_AUTHORIZED_API"
    assert descriptor["status"] == "NOT_CONFIGURED"




def test_authorized_adapter_can_be_injected_behind_same_gateway_interface():
    from app.integrations.government_adapters import GovernmentIntegrationAdapter

    class FakeAuthorizedAdapter(GovernmentIntegrationAdapter):
        system_key = "mpcb"
        display_name = "MPCB"
        is_simulated = False

        async def authenticate(self):
            return {"status": "authenticated"}

        async def get_services(self):
            return []

        async def get_application_status(self, application_id: str):
            return {"application_id": application_id, "status": "SUBMITTED"}

        async def submit_application(self, application_data: dict):
            return {"application_id": "REAL-123", "status": "SUBMITTED"}

    gateway = GovernmentAPIGateway(
        provider="authorized",
        authorized_adapters={"mpcb": FakeAuthorizedAdapter()},
    )
    descriptor = gateway.descriptor("mpcb")
    assert descriptor["classification"] == "AUTHORIZED_API"
    assert descriptor["status"] == "CONNECTED"


def test_service_transparency_distinguishes_modes():
    class Service:
        application_mode = "INTEGRATED"
        is_demo = True
        gateway_system = "mpcb"
        external_portal_url = None

    prototype = service_integration(Service())
    assert prototype["classification"] == "PROTOTYPE_SIMULATOR"
    assert prototype["is_simulated"] is True

    class Redirect:
        application_mode = "REDIRECT"
        is_demo = False
        gateway_system = "gst"
        external_portal_url = "https://www.gst.gov.in"

    external = service_integration(Redirect())
    assert external["classification"] == "EXTERNAL_PORTAL"
    assert external["is_simulated"] is False


def test_gateway_catalog_api_is_available_to_authenticated_applicant():
    response = client.get("/api/gateway/catalog", headers=_auth("ENTREPRENEUR"))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["provider"] == "prototype"
    assert any(item["classification"] == "PROTOTYPE_SIMULATOR" for item in body["systems"])
    assert "disclaimer" in body


def test_gateway_health_exposes_transparent_prototype_status_to_officer():
    response = client.get("/api/gateway/health", headers=_auth("OFFICER"))
    assert response.status_code == 200, response.text
    body = response.json()
    mpcb = body["systems"]["mpcb"]
    assert mpcb["is_simulated"] is True
    assert mpcb["source_label"] == "Prototype Simulator"
    assert mpcb["runtime_status"] in {"HEALTHY", "DEGRADED", "DOWN"}
    assert "disclaimer" in body


def test_gateway_service_adds_integration_metadata_without_changing_payload_contract():
    service = GatewayService()

    async def run():
        result = await service.get_status("mpcb", "MPCB-123456")
        assert "integration" in result
        assert result["integration"]["is_simulated"] is True
        assert result["integration"]["operation"] == "status"

    asyncio.run(run())


def test_explore_service_payload_contains_effective_integration_classification():
    from app.models import GovernmentService

    service = GovernmentService(
        slug="demo-service",
        name="Demo Service",
        category="Testing",
        authority="Prototype Authority",
        department="Testing",
        service_type="APPROVAL",
        application_mode="INTEGRATED",
        is_demo=True,
        is_active=True,
        gateway_system="mpcb",
    )
    payload = __import__("app.api.explore", fromlist=["_service_payload"])._service_payload(service)
    assert payload["integration"]["classification"] == "PROTOTYPE_SIMULATOR"
    assert payload["integration"]["is_simulated"] is True



def test_gateway_catalog_counts_external_portal_systems():
    body = GatewayService().catalog()
    assert body["summary"]["external_portal_systems"] >= 1
    gst = next(item for item in body["systems"] if item["system"] == "gst")
    assert gst["classification"] == "EXTERNAL_PORTAL"
    assert gst["official_portal_url"] == "https://www.gst.gov.in"


def test_authorized_provider_never_falls_back_to_prototype_verification():
    gateway = GatewayService(GovernmentAPIGateway(provider="authorized"))

    async def run():
        result = await gateway.verify("pan", "ABCDE1234F")
        assert result["status"] == "NOT_CONFIGURED"
        assert result["integration"]["classification"] == "FUTURE_AUTHORIZED_API"

    asyncio.run(run())


def test_provider_aliases_normalize_and_invalid_values_fail_closed():
    assert GovernmentAPIGateway(provider="mock").provider == "prototype"
    assert GovernmentAPIGateway(provider="demo").provider == "prototype"
    import pytest
    with pytest.raises(ValueError, match="Unsupported government integration provider"):
        GovernmentAPIGateway(provider="live")
