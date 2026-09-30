"""Regression tests for Step 7 inspection planning and coordination."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.main import app
from app.models import Approval, ApprovalStatus, InspectionVisit, Project, User, UserRole

client = TestClient(app)
PASSWORD = "Password@123"


def _register(email: str, role: str = "ENTREPRENEUR") -> str:
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "name": "Test User",
            "phone": "9876501234",
            "password": PASSWORD,
            "role": role,
        },
    )
    # Public registration may reject privileged roles, so provision them directly below.
    if response.status_code == 201:
        pass
    elif role == "ENTREPRENEUR":
        raise AssertionError(response.text)

    if role != "ENTREPRENEUR":
        async def _seed_privileged():
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(User).where(User.email == email))
                user = result.scalar_one_or_none()
                if user is None:
                    user = User(
                        email=email,
                        name="Officer User",
                        phone="9876501234",
                        password_hash=hash_password(PASSWORD),
                        role=role,
                        is_active=True,
                    )
                    db.add(user)
                    await db.commit()
        asyncio.run(_seed_privileged())

    login = client.post(
        "/api/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _create_project_and_approvals(user_id: uuid.UUID, status=ApprovalStatus.UNDER_REVIEW):
    async def _seed():
        async with AsyncSessionLocal() as db:
            project = Project(
                user_id=user_id,
                name="Inspection Project",
                company_name="Inspection Co",
                industry="Textile",
                sector="Textile",
                location_state="Maharashtra",
                location_district="Nashik",
                location_city="Nashik",
                location_industrial_area="MIDC Ambad",
            )
            db.add(project)
            await db.flush()
            approvals = [
                Approval(
                    project_id=project.id,
                    name="Factory License",
                    department="Factory",
                    status=status,
                    application_id="MAITRI-100001",
                    estimated_processing_days=30,
                    risk_level="MEDIUM",
                    is_mandatory=True,
                ),
                Approval(
                    project_id=project.id,
                    name="Fire NOC",
                    department="Fire",
                    status=status,
                    application_id="FIRE-100001",
                    estimated_processing_days=20,
                    risk_level="MEDIUM",
                    is_mandatory=True,
                ),
            ]
            db.add_all(approvals)
            await db.commit()
            return project.id, [a.id for a in approvals]
    return asyncio.run(_seed())


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


def test_common_visit_coordinates_multiple_inspections_and_advances_workflow():
    entrepreneur_email = f"inspection-owner-{uuid.uuid4().hex[:8]}@example.com"
    token = _register(entrepreneur_email)

    async def _user_id():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.email == entrepreneur_email))
            return result.scalar_one().id

    project_id, approval_ids = _create_project_and_approvals(asyncio.run(_user_id()))
    officer_email = f"inspection-officer-{uuid.uuid4().hex[:8]}@example.com"
    officer_token = _register(officer_email, "OFFICER")

    start = datetime.utcnow() + timedelta(days=2, hours=2)
    end = start + timedelta(hours=2)
    response = client.post(
        "/api/inspections/schedule",
        headers=_auth(officer_token),
        json={
            "approval_ids": [str(x) for x in approval_ids],
            "scheduled_start": start.isoformat(),
            "scheduled_end": end.isoformat(),
            "location": "MIDC Ambad, Nashik",
            "notes": "Coordinate site visit",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["coordinated"] is True
    assert len(body["approvals"]) == 2
    assert body["status"] == "SCHEDULED"
    assert body["location"] == "MIDC Ambad, Nashik"

    async def _check():
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(select(Approval).where(Approval.id.in_(approval_ids)))).scalars().all()
            return [r.status for r in rows]
    statuses = asyncio.run(_check())
    assert all(s == ApprovalStatus.INSPECTION for s in statuses)

    listed = client.get(f"/api/inspections?project_id={project_id}", headers=_auth(token))
    assert listed.status_code == 200, listed.text
    assert listed.json()["inspections"][0]["coordinated"] is True


def test_coordination_suggestion_requires_same_project_candidates():
    email = f"suggest-owner-{uuid.uuid4().hex[:8]}@example.com"
    token = _register(email)

    async def _user_id():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.email == email))
            return result.scalar_one().id

    project_id, approval_ids = _create_project_and_approvals(asyncio.run(_user_id()))
    response = client.get(
        f"/api/inspections/coordination-suggestions?project_id={project_id}",
        headers=_auth(token),
    )
    assert response.status_code == 200, response.text
    suggestions = response.json()["suggestions"]
    assert len(suggestions) == 1
    suggestion = suggestions[0]
    assert suggestion["approval_count"] == 2
    assert suggestion["site_visits_avoided"] == 1
    assert suggestion["project_id"] == str(project_id)
    assert set(suggestion["approval_ids"]) == {str(x) for x in approval_ids}


def test_entrepreneur_cannot_schedule_or_discover_all_projects():
    owner_email = f"schedule-owner-{uuid.uuid4().hex[:8]}@example.com"
    token = _register(owner_email)
    other_email = f"schedule-other-{uuid.uuid4().hex[:8]}@example.com"
    _register(other_email)

    async def _ids():
        async with AsyncSessionLocal() as db:
            r1 = await db.execute(select(User).where(User.email == owner_email))
            r2 = await db.execute(select(User).where(User.email == other_email))
            return r1.scalar_one().id, r2.scalar_one().id

    owner_id, other_id = asyncio.run(_ids())
    project_id, approval_ids = _create_project_and_approvals(owner_id)
    other_project_id, _ = _create_project_and_approvals(other_id)

    start = datetime.utcnow() + timedelta(days=3)
    response = client.post(
        "/api/inspections/schedule",
        headers=_auth(token),
        json={
            "approval_ids": [str(approval_ids[0])],
            "scheduled_start": start.isoformat(),
            "scheduled_end": (start + timedelta(hours=1)).isoformat(),
        },
    )
    assert response.status_code == 403

    response = client.get(
        "/api/inspections/coordination-suggestions",
        headers=_auth(token),
    )
    assert response.status_code == 200, response.text
    assert response.json()["suggestions"][0]["project_id"] == str(project_id)
    assert all(item["project_id"] != str(other_project_id) for item in response.json()["suggestions"])

    response = client.get(
        f"/api/inspections?project_id={other_project_id}",
        headers=_auth(token),
    )
    assert response.status_code == 403


def test_officer_conflicting_schedule_is_blocked():
    owner_email = f"conflict-owner-{uuid.uuid4().hex[:8]}@example.com"
    _register(owner_email)
    async def _owner():
        async with AsyncSessionLocal() as db:
            return (await db.execute(select(User).where(User.email == owner_email))).scalar_one().id
    owner_id = asyncio.run(_owner())
    project_id, approval_ids = _create_project_and_approvals(owner_id)
    officer_email = f"conflict-officer-{uuid.uuid4().hex[:8]}@example.com"
    officer_token = _register(officer_email, "OFFICER")

    async def _officer_id():
        async with AsyncSessionLocal() as db:
            return (await db.execute(select(User).where(User.email == officer_email))).scalar_one().id
    officer_id = asyncio.run(_officer_id())

    start = datetime.utcnow() + timedelta(days=4, hours=1)
    end = start + timedelta(hours=1)
    first = client.post(
        "/api/inspections/schedule",
        headers=_auth(officer_token),
        json={
            "approval_ids": [str(approval_ids[0])],
            "scheduled_start": start.isoformat(),
            "scheduled_end": end.isoformat(),
            "assigned_officer_id": str(officer_id),
        },
    )
    assert first.status_code == 200, first.text

    async def _new_approval():
        async with AsyncSessionLocal() as db:
            a = Approval(
                project_id=project_id,
                name="Boiler Registration",
                department="Boiler",
                status=ApprovalStatus.UNDER_REVIEW,
                application_id="BOILER-100001",
                estimated_processing_days=15,
                risk_level="HIGH",
                is_mandatory=True,
            )
            db.add(a)
            await db.commit()
            return a.id
    new_id = asyncio.run(_new_approval())

    conflict = client.post(
        "/api/inspections/schedule",
        headers=_auth(officer_token),
        json={
            "approval_ids": [str(new_id)],
            "scheduled_start": (start + timedelta(minutes=30)).isoformat(),
            "scheduled_end": (end + timedelta(minutes=30)).isoformat(),
            "assigned_officer_id": str(officer_id),
        },
    )
    assert conflict.status_code == 400
    assert "another inspection" in conflict.json()["detail"]


def test_application_inspection_endpoint_and_update_lifecycle():
    owner_email = f"update-owner-{uuid.uuid4().hex[:8]}@example.com"
    owner_token = _register(owner_email)
    async def _owner():
        async with AsyncSessionLocal() as db:
            return (await db.execute(select(User).where(User.email == owner_email))).scalar_one().id
    owner_id = asyncio.run(_owner())
    project_id, approval_ids = _create_project_and_approvals(owner_id)
    officer_email = f"update-officer-{uuid.uuid4().hex[:8]}@example.com"
    officer_token = _register(officer_email, "OFFICER")

    start = datetime.utcnow() + timedelta(days=5)
    created = client.post(
        "/api/inspections/schedule",
        headers=_auth(officer_token),
        json={
            "approval_ids": [str(approval_ids[0])],
            "scheduled_start": start.isoformat(),
            "scheduled_end": (start + timedelta(hours=1)).isoformat(),
        },
    )
    assert created.status_code == 200, created.text
    visit_id = created.json()["id"]
    application_response = client.get(
        "/api/inspections/application/MAITRI-100001",
        headers=_auth(owner_token),
    )
    assert application_response.status_code == 200, application_response.text
    assert application_response.json()["inspections"]

    updated = client.patch(
        f"/api/inspections/{visit_id}",
        headers=_auth(officer_token),
        json={"status": "COMPLETED", "notes": "Inspection completed in prototype workflow"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["status"] == "COMPLETED"

    async def _approval_status():
        async with AsyncSessionLocal() as db:
            a = (await db.execute(select(Approval).where(Approval.id == approval_ids[0]))).scalar_one()
            v = (await db.execute(select(InspectionVisit).where(InspectionVisit.id == uuid.UUID(visit_id)))).scalar_one()
            return a.status, v.status
    approval_status, visit_status = asyncio.run(_approval_status())
    assert approval_status == ApprovalStatus.INSPECTION
    assert visit_status == "COMPLETED"


def test_officer_can_update_checklist_without_changing_approval_decision():
    owner_email = f"check-owner-{uuid.uuid4().hex[:8]}@example.com"
    _register(owner_email)
    async def _owner():
        async with AsyncSessionLocal() as db:
            return (await db.execute(select(User).where(User.email == owner_email))).scalar_one().id
    owner_id = asyncio.run(_owner())
    _project_id, approval_ids = _create_project_and_approvals(owner_id)
    officer_email = f"check-officer-{uuid.uuid4().hex[:8]}@example.com"
    officer_token = _register(officer_email, "OFFICER")
    start = datetime.utcnow() + timedelta(days=6)
    created = client.post(
        "/api/inspections/schedule",
        headers=_auth(officer_token),
        json={
            "approval_ids": [str(approval_ids[0])],
            "scheduled_start": start.isoformat(),
            "scheduled_end": (start + timedelta(hours=1)).isoformat(),
        },
    )
    assert created.status_code == 200, created.text
    visit = created.json()
    checklist = visit["checklist"]
    checklist[0]["completed"] = True
    updated = client.patch(
        f"/api/inspections/{visit['id']}",
        headers=_auth(officer_token),
        json={"checklist": checklist},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["checklist"][0]["completed"] is True
    assert updated.json()["approvals"][0]["status"] == "INSPECTION"


def test_officer_list_can_filter_by_assignee_and_officers_endpoint_is_protected():
    owner_email = f"filter-owner-{uuid.uuid4().hex[:8]}@example.com"
    _register(owner_email)
    async def _owner():
        async with AsyncSessionLocal() as db:
            return (await db.execute(select(User).where(User.email == owner_email))).scalar_one().id
    owner_id = asyncio.run(_owner())
    _project_id, approval_ids = _create_project_and_approvals(owner_id)
    officer_email = f"filter-officer-{uuid.uuid4().hex[:8]}@example.com"
    officer_token = _register(officer_email, "OFFICER")
    async def _officer():
        async with AsyncSessionLocal() as db:
            return (await db.execute(select(User).where(User.email == officer_email))).scalar_one().id
    officer_id = asyncio.run(_officer())
    start = datetime.utcnow() + timedelta(days=7)
    created = client.post(
        "/api/inspections/schedule",
        headers=_auth(officer_token),
        json={
            "approval_ids": [str(approval_ids[0])],
            "scheduled_start": start.isoformat(),
            "scheduled_end": (start + timedelta(hours=1)).isoformat(),
            "assigned_officer_id": str(officer_id),
        },
    )
    assert created.status_code == 200, created.text
    listed = client.get(
        f"/api/inspections?assigned_officer_id={officer_id}",
        headers=_auth(officer_token),
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["inspections"][0]["assigned_officer_id"] == str(officer_id)
    officers = client.get("/api/inspections/officers", headers=_auth(officer_token))
    assert officers.status_code == 200, officers.text
    assert any(item["id"] == str(officer_id) for item in officers.json()["officers"])

    entrepreneur = client.get("/api/inspections/officers", headers=_auth(_register(f"filter-user-{uuid.uuid4().hex[:8]}@example.com")))
    assert entrepreneur.status_code == 403
