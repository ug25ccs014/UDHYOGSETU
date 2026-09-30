"""HTTP coverage for Step 8 SLA + smart-risk APIs."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.main import app
from app.models import Approval, ApprovalStatus, Project, User, UserRole

client = TestClient(app)
PASSWORD = "Password@123"


def _email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


def _register_entrepreneur() -> tuple[str, dict]:
    email = _email("sla-api")
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "name": "SLA User",
            "phone": "9876505555",
            "password": PASSWORD,
            "role": "ENTREPRENEUR",
        },
    )
    assert response.status_code == 201, response.text
    login = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    return email, {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_project(email: str, headers: dict) -> str:
    response = client.post(
        "/api/projects",
        headers=headers,
        json={
            "company_name": "SLA API Industries",
            "business_type": "manufacturing",
            "industry": "Textiles",
            "sector": "Textile",
            "project_name": "SLA API Project",
            "is_new": True,
            "project_stage": "implementation",
            "investment_amount": 2000000,
            "location_state": "Maharashtra",
            "location_district": "Pune",
            "location_city": "Pune",
            "location_industrial_area": "MIDC",
            "land_type": "leased",
            "employees": 20,
            "has_boiler": False,
            "pollution_potential": "low",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _seed_approval(email: str, project_id: str) -> str:
    async def _seed():
        async with AsyncSessionLocal() as db:
            user = (await db.execute(select(User).where(User.email == email))).scalar_one()
            approval = Approval(
                project_id=uuid.UUID(project_id),
                name="SLA API Approval",
                department="MPCB",
                status=ApprovalStatus.SUBMITTED,
                submitted_at=datetime.now(timezone.utc) - timedelta(days=50),
                estimated_processing_days=60,
            )
            db.add(approval)
            await db.commit()
            return str(approval.id)

    return asyncio.run(_seed())


def _provision_officer() -> dict:
    email = _email("officer-sla")

    async def _seed():
        async with AsyncSessionLocal() as db:
            user = User(
                email=email,
                name="SLA Officer",
                phone="9876505666",
                password_hash=hash_password(PASSWORD),
                role=UserRole.OFFICER,
                is_active=True,
            )
            db.add(user)
            await db.commit()

    asyncio.run(_seed())
    login = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_portfolio_endpoint_is_owner_scoped_and_reports_sla_signal():
    email, headers = _register_entrepreneur()
    project_id = _create_project(email, headers)
    approval_id = _seed_approval(email, project_id)

    response = client.get("/api/sla-risk/portfolio", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_applications"] == 1
    assert body["sla_at_risk"] == 1
    assert body["applications"][0]["approval_id"] == approval_id


def test_officer_queue_requires_officer_role():
    _, entrepreneur_headers = _register_entrepreneur()
    forbidden = client.get("/api/sla-risk/officer", headers=entrepreneur_headers)
    assert forbidden.status_code == 403, forbidden.text

    officer_headers = _provision_officer()
    allowed = client.get("/api/sla-risk/officer", headers=officer_headers)
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["scope"] == "OFFICER"
