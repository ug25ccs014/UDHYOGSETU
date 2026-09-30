"""Regression tests for Step 9 grievance and escalation management."""

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token, hash_password
from app.models import Approval, Grievance, GrievanceEvent, Project, User, UserRole
from app.services.grievance import GrievanceService


async def _make_case(db):
    owner = User(
        id=uuid.uuid4(), email=f"g-{uuid.uuid4().hex[:8]}@example.com", name="Grievance Owner",
        phone="9876543210", password_hash=hash_password("Password@123"), role=UserRole.ENTREPRENEUR,
    )
    officer = User(
        id=uuid.uuid4(), email=f"o-{uuid.uuid4().hex[:8]}@example.com", name="Review Officer",
        phone="9876543211", password_hash=hash_password("Password@123"), role=UserRole.OFFICER,
    )
    db.add_all([owner, officer])
    await db.flush()
    project = Project(
        user_id=owner.id, name="Grievance Project", company_name="Grievance Co", industry="Textile",
        sector="Textile", investment_amount=2000000, employees=40, location_state="Maharashtra",
        location_district="Pune", location_city="Pune",
    )
    db.add(project)
    await db.flush()
    approval = Approval(
        project_id=project.id, application_id="MPCB-100001", name="MPCB Consent",
        department="MPCB", status="UNDER_REVIEW", submitted_at=datetime.utcnow() - timedelta(days=50),
        estimated_processing_days=60,
    )
    db.add(approval)
    await db.commit()
    return owner, officer, project, approval


@pytest.mark.asyncio
async def test_grievance_create_and_event_timeline():
    async with AsyncSessionLocal() as db:
        owner, _officer, project, approval = await _make_case(db)
        service = GrievanceService(db)
        grievance = await service.create(
            owner.id, application_id=approval.application_id, project_id=project.id,
            category="SLA Concern", subject="Application nearing SLA", description="Please review the pending application because the configured target is approaching.", priority="HIGH",
        )
        payload = await service.serialize(grievance)
        assert payload["status"] == "OPEN"
        assert payload["application_id"] == "MPCB-100001"
        assert payload["escalation_level"] == 0
        assert len(payload["events"]) == 1
        assert payload["sla_context"]["sla"]["status"] in {"AT_RISK", "BREACHED"}


@pytest.mark.asyncio
async def test_grievance_applicant_can_request_escalation_then_officer_can_escalate_again_and_resolve():
    async with AsyncSessionLocal() as db:
        owner, officer, project, approval = await _make_case(db)
        service = GrievanceService(db)
        grievance = await service.create(
            owner.id, application_id=approval.application_id, project_id=project.id,
            category="Application Delay", subject="Need status update", description="The application has remained under review and needs a status update.", priority="MEDIUM",
        )

        grievance = await service.request_escalation(grievance.id, owner.id, "ENTREPRENEUR", "SLA is approaching and I have had no update.")
        assert grievance.status == "ESCALATED"
        assert grievance.escalation_level == 1

        grievance = await service.request_escalation(grievance.id, officer.id, "OFFICER", "Department desk review is complete; escalating to senior review.")
        assert grievance.status == "ESCALATED"
        assert grievance.escalation_level == 2

        grievance = await service.transition(
            grievance.id, actor_user_id=officer.id, actor_role="OFFICER", to_status="RESOLVED",
            resolution_note="Status reviewed and applicant response recorded.",
        )
        assert grievance.status == "RESOLVED"
        assert grievance.resolved_at is not None

        closed = await service.transition(grievance.id, actor_user_id=owner.id, actor_role="ENTREPRENEUR", to_status="CLOSED")
        assert closed.status == "CLOSED"

        events = list((await db.execute(select(GrievanceEvent).where(GrievanceEvent.grievance_id == grievance.id))).scalars().all())
        assert any(event.event_type == "ESCALATION_LEVEL_CHANGED" for event in events)


@pytest.mark.asyncio
async def test_grievance_owner_isolation_and_terminal_protection():
    async with AsyncSessionLocal() as db:
        owner, officer, project, approval = await _make_case(db)
        other = User(
            id=uuid.uuid4(), email=f"other-{uuid.uuid4().hex[:8]}@example.com", name="Other",
            phone="9876543212", password_hash=hash_password("Password@123"), role=UserRole.ENTREPRENEUR,
        )
        db.add(other)
        await db.commit()
        service = GrievanceService(db)
        grievance = await service.create(
            owner.id, application_id=approval.application_id, project_id=project.id,
            category="Other", subject="Test grievance", description="This is a test grievance for ownership checks.", priority="LOW",
        )
        with pytest.raises(ValueError, match="authorized"):
            await service.transition(grievance.id, actor_user_id=other.id, actor_role="ENTREPRENEUR", to_status="CLOSED")
        grievance = await service.transition(
            grievance.id, actor_user_id=officer.id, actor_role="OFFICER", to_status="REJECTED", note="Not substantiated.",
        )
        assert grievance.status == "REJECTED"
        with pytest.raises(ValueError, match="cannot be escalated"):
            await service.request_escalation(grievance.id, owner.id, "ENTREPRENEUR", "Try again")


@pytest.mark.asyncio
async def test_grievance_http_create_list_and_transition_owner_scoped():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    async with AsyncSessionLocal() as db:
        owner, officer, project, approval = await _make_case(db)
        owner_token = create_access_token({"sub": str(owner.id), "email": owner.email, "role": "ENTREPRENEUR"})
        officer_token = create_access_token({"sub": str(officer.id), "email": officer.email, "role": "OFFICER"})

    created = client.post(
        "/api/grievances",
        json={"application_id": approval.application_id, "category": "SLA Concern", "subject": "Please review", "description": "My application is close to the configured processing target.", "priority": "HIGH"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert created.status_code == 200, created.text
    grievance_id = created.json()["id"]

    listed = client.get("/api/grievances", headers={"Authorization": f"Bearer {owner_token}"})
    assert listed.status_code == 200
    assert len(listed.json()["grievances"]) == 1

    updated = client.post(
        f"/api/grievances/{grievance_id}/transition",
        json={"to_status": "ACKNOWLEDGED", "note": "Case received."},
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["status"] == "ACKNOWLEDGED"

    summary = client.get("/api/grievances/summary", headers={"Authorization": f"Bearer {owner_token}"})
    assert summary.status_code == 200
    assert summary.json()["total"] == 1
