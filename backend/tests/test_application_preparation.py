"""Tests for applicant-side application auto-prefill and preparation."""

from __future__ import annotations

import asyncio
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.main import app
from app.models import Approval, ApprovalRule, BusinessProfile, Document, Project, User

client = TestClient(app)
PASSWORD = "Password@123"


def _email(prefix="prep"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


def _auth():
    email = _email()
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "name": "Preparation User",
            "phone": "9876543210",
            "password": PASSWORD,
            "role": "ENTREPRENEUR",
        },
    )
    assert response.status_code == 201, response.text
    login = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    return email, {"Authorization": f"Bearer {login.json()['access_token']}"}


def _project(headers):
    response = client.post(
        "/api/projects",
        headers=headers,
        json={
            "company_name": "Prep Industries Pvt Ltd",
            "business_type": "manufacturing",
            "industry": "Textiles",
            "sector": "Textile",
            "project_name": "Prep Factory",
            "is_new": True,
            "project_stage": "implementation",
            "investment_amount": 2500000,
            "location_state": "Maharashtra",
            "location_district": "Pune",
            "location_city": "Pune",
            "location_industrial_area": "MIDC",
            "location_midc_estate": "MIDC",
            "land_type": "leased",
            "employees": 60,
            "production_type": "batch",
            "hazardous_materials": False,
            "has_boiler": False,
            "electricity_load": 120,
            "water_consumption": 400,
            "pollution_potential": "medium",
            "building_type": "industrial",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _seed_application(email: str, project_id: str):
    async def _seed():
        async with AsyncSessionLocal() as db:
            user = (await db.execute(select(User).where(User.email == email))).scalar_one()
            db.add(
                BusinessProfile(
                    user_id=user.id,
                    company_name="Prep Industries Pvt Ltd",
                    business_type="manufacturing",
                    industry="Textiles",
                    sector="Textile",
                    pan="ABCDE1234F",
                    gstin="27ABCDE1234F1Z5",
                    udyam_number="UDYAM-MH-18-0001234",
                    registered_address="123 MIDC Road",
                    registered_state="Maharashtra",
                    registered_district="Pune",
                    registered_city="Pune",
                    registered_pincode="411001",
                )
            )
            rule = ApprovalRule(
                name="Prep Test Rule",
                department="Test Department",
                conditions={},
                required_documents=["PAN Card"],
                dependencies=[],
                estimated_processing_days=7,
            )
            db.add(rule)
            await db.flush()
            approval = Approval(
                project_id=uuid.UUID(project_id),
                name=rule.name,
                department=rule.department,
                status="DRAFT",
            )
            db.add(approval)
            await db.commit()
            return str(approval.id)

    return asyncio.run(_seed())


def test_preparation_auto_prefills_from_profile_and_project():
    email, headers = _auth()
    project = _project(headers)
    application_id = _seed_application(email, project["id"])

    response = client.get(f"/api/applications/{application_id}/preparation", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    fields = {field["key"]: field for field in body["fields"]}

    assert fields["company_name"]["value"] == "Prep Industries Pvt Ltd"
    assert fields["company_name"]["effective_source"] == "BUSINESS_PROFILE"
    assert fields["project_name"]["value"] == "Prep Factory"
    assert fields["project_name"]["effective_source"] == "PROJECT"
    assert fields["pan"]["required"] is True
    assert body["summary"]["preparation_score"] == 100
    assert body["status"] == "DRAFT"


def test_preparation_saves_user_override_without_overwriting_profile():
    email, headers = _auth()
    project = _project(headers)
    application_id = _seed_application(email, project["id"])

    response = client.patch(
        f"/api/applications/{application_id}/preparation",
        headers=headers,
        json={"overrides": {"company_name": "Project-Specific Name"}},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    field = next(f for f in body["fields"] if f["key"] == "company_name")
    assert field["value"] == "Project-Specific Name"
    assert field["effective_source"] == "USER_OVERRIDE"
    assert field["has_override"] is True

    profile = client.get("/api/profile", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["company_name"] == "Prep Industries Pvt Ltd"


def test_preparation_can_mark_prepared_and_snapshots_values():
    email, headers = _auth()
    project = _project(headers)
    application_id = _seed_application(email, project["id"])

    response = client.patch(
        f"/api/applications/{application_id}/preparation",
        headers=headers,
        json={"overrides": {"project_stage": "operation"}, "mark_prepared": True},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "PREPARED"
    assert body["prepared_at"]
    assert next(f for f in body["fields"] if f["key"] == "project_stage")["value"] == "operation"

    async def _change_project():
        async with AsyncSessionLocal() as db:
            project_row = (await db.execute(select(Project).where(Project.id == uuid.UUID(project["id"])))).scalar_one()
            project_row.location_city = "Nashik"
            await db.commit()

    asyncio.run(_change_project())

    stale = client.get(f"/api/applications/{application_id}/preparation", headers=headers)
    assert stale.status_code == 200, stale.text
    stale_body = stale.json()
    assert stale_body["status"] == "STALE"
    assert "Project City" in stale_body["stale_fields"]
    assert next(f for f in stale_body["fields"] if f["key"] == "location_city")["value"] == "Pune"


def test_preparation_mark_prepared_rejects_missing_required_field():
    email, headers = _auth()
    project = _project(headers)
    application_id = _seed_application(email, project["id"])

    async def _clear_required():
        async with AsyncSessionLocal() as db:
            project_row = (await db.execute(select(Project).where(Project.id == uuid.UUID(project["id"])))).scalar_one()
            project_row.project_stage = None
            await db.commit()

    asyncio.run(_clear_required())

    response = client.patch(
        f"/api/applications/{application_id}/preparation",
        headers=headers,
        json={"mark_prepared": True},
    )
    assert response.status_code == 400, response.text
    assert "Project Stage" in response.json()["detail"]


def test_preparation_rejects_cross_project_document_selection():
    email, headers = _auth()
    project = _project(headers)
    application_id = _seed_application(email, project["id"])

    async def _seed_other_project_document():
        async with AsyncSessionLocal() as db:
            user = (await db.execute(select(User).where(User.email == email))).scalar_one()
            other = Project(
                user_id=user.id,
                name="Other Project",
                company_name="Prep Industries Pvt Ltd",
                business_type="manufacturing",
                industry="Textiles",
                sector="Textile",
            )
            db.add(other)
            await db.flush()
            doc = Document(
                project_id=other.id,
                file_name="other.pdf",
                file_path="/tmp/other.pdf",
                file_type="application/pdf",
                status="VERIFIED",
                extracted_fields={},
                validation_errors=[],
            )
            db.add(doc)
            await db.commit()
            return str(doc.id)

    document_id = asyncio.run(_seed_other_project_document())
    response = client.patch(
        f"/api/applications/{application_id}/preparation",
        headers=headers,
        json={"document_ids": [document_id]},
    )
    assert response.status_code == 400, response.text
    assert "does not belong" in response.json()["detail"].lower()


def test_preparation_supports_non_uuid_government_application_id():
    email, headers = _auth()
    project = _project(headers)
    application_id = _seed_application(email, project["id"])

    async def _set_government_id():
        async with AsyncSessionLocal() as db:
            approval = (await db.execute(select(Approval).where(Approval.id == uuid.UUID(application_id)))).scalar_one()
            approval.application_id = "MPCB-123456"
            await db.commit()

    asyncio.run(_set_government_id())
    response = client.patch(
        "/api/applications/MPCB-123456/preparation",
        headers=headers,
        json={"overrides": {"project_stage": "operation"}},
    )
    assert response.status_code == 200, response.text
    assert next(field for field in response.json()["fields"] if field["key"] == "project_stage")["value"] == "operation"


def test_preparation_marks_source_changes_and_can_reset_to_latest_source():
    email, headers = _auth()
    project = _project(headers)
    application_id = _seed_application(email, project["id"])

    prepared = client.patch(
        f"/api/applications/{application_id}/preparation",
        headers=headers,
        json={"mark_prepared": True},
    )
    assert prepared.status_code == 200, prepared.text

    async def _change_project():
        async with AsyncSessionLocal() as db:
            row = (await db.execute(select(Project).where(Project.id == uuid.UUID(project["id"])))).scalar_one()
            row.location_city = "Nashik"
            await db.commit()

    asyncio.run(_change_project())
    stale = client.get(f"/api/applications/{application_id}/preparation", headers=headers)
    assert stale.status_code == 200, stale.text
    field = next(item for item in stale.json()["fields"] if item["key"] == "location_city")
    assert field["source_changed"] is True
    assert field["value"] == "Pune"
    assert field["source_value"] == "Nashik"
    assert field["effective_source"] == "PREPARED_SNAPSHOT"

    reset = client.patch(
        f"/api/applications/{application_id}/preparation",
        headers=headers,
        json={"reset_fields": ["location_city"]},
    )
    assert reset.status_code == 200, reset.text
    reset_field = next(item for item in reset.json()["fields"] if item["key"] == "location_city")
    assert reset_field["value"] == "Nashik"
    assert reset_field["effective_source"] == "PROJECT"
    assert reset.json()["status"] == "DRAFT"


def test_preparation_is_locked_after_submission():
    email, headers = _auth()
    project = _project(headers)
    application_id = _seed_application(email, project["id"])

    async def _submit():
        async with AsyncSessionLocal() as db:
            approval = (await db.execute(select(Approval).where(Approval.id == uuid.UUID(application_id)))).scalar_one()
            approval.status = "SUBMITTED"
            await db.commit()

    asyncio.run(_submit())
    response = client.patch(
        f"/api/applications/{application_id}/preparation",
        headers=headers,
        json={"overrides": {"project_stage": "operation"}},
    )
    assert response.status_code == 400, response.text
    assert "before submission" in response.json()["detail"].lower()
