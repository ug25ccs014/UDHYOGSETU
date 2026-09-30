"""HTTP contract coverage for the pre-submission readiness gate."""

from __future__ import annotations

import asyncio
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.main import app
from app.models import Approval, ApprovalRule, Document, DocumentStatus, User

client = TestClient(app)
PASSWORD = "Password@123"


def _email(prefix="readiness-api"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


def _auth():
    email = _email()
    registered = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "name": "Readiness API User",
            "phone": "9876543210",
            "password": PASSWORD,
            "role": "ENTREPRENEUR",
        },
    )
    assert registered.status_code == 201, registered.text
    login = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    return email, {"Authorization": f"Bearer {login.json()['access_token']}"}


def _project(headers):
    response = client.post(
        "/api/projects",
        json={
            "company_name": "Readiness Industries Pvt Ltd",
            "business_type": "manufacturing",
            "industry": "Textiles",
            "sector": "Textile",
            "project_name": "Readiness Factory",
            "is_new": True,
            "project_stage": "implementation",
            "investment_amount": 5000000,
            "location_state": "Maharashtra",
            "location_district": "Pune",
            "location_city": "Pune",
            "location_industrial_area": "MIDC",
            "location_midc_estate": "MIDC",
            "land_type": "leased",
            "employees": 120,
            "production_type": "continuous",
            "hazardous_materials": False,
            "has_boiler": False,
            "electricity_load": 100,
            "water_consumption": 500,
            "pollution_potential": "medium",
            "building_type": "industrial",
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_readiness_endpoint_returns_actionable_blockers():
    email, headers = _auth()
    project = _project(headers)

    async def _seed_approval():
        async with AsyncSessionLocal() as db:
            user = (await db.execute(select(User).where(User.email == email))).scalar_one()
            rule = ApprovalRule(
                name="Readiness Fire Rule",
                department="Fire Services Department",
                conditions={},
                required_documents=["Building Layout", "Fire Safety Plan"],
            )
            db.add(rule)
            await db.flush()
            approval = Approval(
                project_id=uuid.UUID(project["id"]),
                name=rule.name,
                department=rule.department,
                status="DRAFT",
            )
            db.add(approval)
            await db.commit()
            return str(approval.id), user.id

    approval_id, _ = asyncio.run(_seed_approval())
    response = client.get(f"/api/applications/{approval_id}/readiness", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["readiness_state"] == "BLOCKED"
    assert body["can_submit"] is False
    assert body["summary"]["documents_missing"] == 2
    assert body["next_actions"]


def test_submit_is_blocked_until_readiness_passes():
    email, headers = _auth()
    project = _project(headers)

    async def _seed_approval():
        async with AsyncSessionLocal() as db:
            rule = ApprovalRule(
                name="Readiness Submit Rule",
                department="Test Department",
                conditions={},
                required_documents=["PAN Card"],
            )
            db.add(rule)
            await db.flush()
            approval = Approval(
                project_id=uuid.UUID(project["id"]),
                name=rule.name,
                department=rule.department,
                status="DRAFT",
            )
            db.add(approval)
            await db.commit()
            return str(approval.id)

    approval_id = asyncio.run(_seed_approval())
    blocked = client.post(f"/api/applications/{approval_id}/submit", headers=headers)
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["detail"]["code"] == "PRE_SUBMISSION_READINESS_BLOCKED"
    assert blocked.json()["detail"]["readiness"]["summary"]["documents_missing"] == 1


def test_transition_to_submitted_is_also_blocked_by_readiness():
    email, headers = _auth()
    project = _project(headers)

    async def _seed_approval():
        async with AsyncSessionLocal() as db:
            rule = ApprovalRule(
                name="Readiness Transition Rule",
                department="Test Department",
                conditions={},
                required_documents=["PAN Card"],
            )
            db.add(rule)
            await db.flush()
            approval = Approval(
                project_id=uuid.UUID(project["id"]),
                name=rule.name,
                department=rule.department,
                status="DRAFT",
            )
            db.add(approval)
            await db.commit()
            return str(approval.id)

    approval_id = asyncio.run(_seed_approval())
    blocked = client.post(
        f"/api/applications/{approval_id}/transition",
        json={"to_status": "SUBMITTED"},
        headers=headers,
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["detail"]["code"] == "PRE_SUBMISSION_READINESS_BLOCKED"


def test_application_document_attach_is_project_scoped():
    email, headers = _auth()
    project = _project(headers)

    async def _seed_approval_and_document():
        async with AsyncSessionLocal() as db:
            approval = Approval(
                project_id=uuid.UUID(project["id"]),
                name="Attach Rule",
                department="Test Department",
                status="DRAFT",
            )
            document = Document(
                project_id=uuid.UUID(project["id"]),
                file_name="pan_card.pdf",
                file_path="/tmp/pan_card.pdf",
                file_type="application/pdf",
                status=DocumentStatus.VERIFIED,
                extracted_fields={"document_type": "PAN CARD", "pan": "ABCDE1234F", "name": "Readiness Industries Pvt Ltd"},
                validation_errors=[],
            )
            db.add_all([approval, document])
            await db.commit()
            return str(approval.id), str(document.id)

    approval_id, document_id = asyncio.run(_seed_approval_and_document())
    response = client.post(
        f"/api/applications/{approval_id}/documents/{document_id}",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["attached"] is True
