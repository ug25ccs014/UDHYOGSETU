"""Step 16 API regression tests."""

import asyncio
import uuid

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import AsyncSessionLocal
from app.models import ApprovalRule

client = TestClient(app)
PASSWORD = "Password@123"


def _email(prefix="scenario-api"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


def _headers():
    email = _email()
    r = client.post("/api/auth/register", json={
        "email": email,
        "name": "Scenario API User",
        "phone": "9876543210",
        "password": PASSWORD,
        "role": "ENTREPRENEUR",
    })
    assert r.status_code == 201, r.text
    r = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _insert_rules():
    async def run():
        async with AsyncSessionLocal() as session:
            session.add_all([
                ApprovalRule(
                    name="Factory License",
                    department="Factory",
                    sector="Manufacturing",
                    conditions={"type": "COMPARISON", "field": "employees", "operator": "greater_than", "value": 9},
                    is_mandatory=True,
                    required_documents=["Factory Plan"],
                    estimated_processing_days=30,
                    risk_level="MEDIUM",
                    dependencies=[],
                ),
                ApprovalRule(
                    name="Boiler Registration",
                    department="Boiler",
                    sector="Manufacturing",
                    conditions={"type": "COMPARISON", "field": "has_boiler", "operator": "equals", "value": True},
                    is_mandatory=True,
                    required_documents=["Boiler Specification"],
                    estimated_processing_days=15,
                    risk_level="HIGH",
                    dependencies=["Factory License"],
                ),
            ])
            await session.commit()
    asyncio.run(run())


def _project_payload():
    return {
        "company_name": "Scenario API Industries",
        "business_type": "manufacturing",
        "industry": "Manufacturing",
        "sector": "Manufacturing",
        "project_name": "Scenario API Project",
        "is_new": True,
        "project_stage": "feasibility",
        "investment_amount": 5_000_000,
        "location_state": "Maharashtra",
        "location_district": "Pune",
        "location_city": "Pune",
        "location_industrial_area": "MIDC",
        "location_midc_estate": "MIDC",
        "land_type": "leased",
        "employees": 5,
        "production_type": "continuous",
        "hazardous_materials": False,
        "has_boiler": False,
        "electricity_load": 100,
        "water_consumption": 500,
        "pollution_potential": "low",
        "building_type": "industrial",
    }


def test_scenario_catalog_requires_auth():
    r = client.get("/api/simulate/catalog")
    assert r.status_code == 401


def test_project_scenario_route_is_owner_scoped():
    owner = _headers()
    other = _headers()
    r = client.post("/api/projects", json=_project_payload(), headers=owner)
    assert r.status_code == 200, r.text
    project_id = r.json()["id"]
    _insert_rules()
    r = client.post(
        f"/api/simulate/projects/{project_id}",
        json={"scenario_type": "boiler_addition", "parameters": {"has_boiler": True}},
        headers=other,
    )
    assert r.status_code == 403


def test_project_scenario_route_returns_projection():
    headers = _headers()
    r = client.post("/api/projects", json=_project_payload(), headers=headers)
    assert r.status_code == 200, r.text
    project_id = r.json()["id"]
    _insert_rules()
    r = client.post(
        f"/api/simulate/projects/{project_id}",
        json={"scenario_type": "boiler_addition", "parameters": {"has_boiler": True}},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scenario"]["type"] == "boiler_addition"
    assert "Boiler Registration" in {x["name"] for x in body["changes"]["approvals_added"]}
    assert body["warnings"]
