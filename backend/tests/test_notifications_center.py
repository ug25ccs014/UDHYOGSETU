"""Regression coverage for the Step 12 notification center."""

import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.main import app
from app.models import Notification, Project, User, UserRole
from app.notifications.service import NotificationService


async def _users(db):
    owner = User(
        id=uuid.uuid4(),
        email=f"notify-center-{uuid.uuid4().hex[:8]}@example.com",
        name="Notification Owner",
        phone="9876505555",
        password_hash=hash_password("Password@123"),
        role=UserRole.ENTREPRENEUR,
    )
    other = User(
        id=uuid.uuid4(),
        email=f"notify-other-{uuid.uuid4().hex[:8]}@example.com",
        name="Other Owner",
        phone="9876505556",
        password_hash=hash_password("Password@123"),
        role=UserRole.ENTREPRENEUR,
    )
    db.add_all([owner, other])
    await db.commit()
    await db.refresh(owner)
    await db.refresh(other)
    return owner, other


def _headers(user):
    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_notification_summary_and_filters(db_session):
    owner, _ = await _users(db_session)
    svc = NotificationService(db_session)
    await svc.create(owner.id, "Approval", "Approved", category="approval", severity="success")
    await svc.create(owner.id, "Query", "Needs action", category="query", severity="warning")
    unread = await svc.summary(owner.id)
    assert unread["total"] == 2
    assert unread["unread"] == 2
    assert unread["by_category"] == {"approval": 1, "query": 1}
    rows = await svc.list_for_user(owner.id, unread_only=True, category="query")
    assert len(rows) == 1
    assert rows[0].category == "query"


@pytest.mark.asyncio
async def test_notification_create_once_deduplicates_recent_event(db_session):
    owner, _ = await _users(db_session)
    svc = NotificationService(db_session)
    first = await svc.create_once(
        owner.id,
        "SLA Breach Alert",
        "Same event",
        category="sla",
        severity="error",
        reference_id="APP-001",
        window_minutes=60,
    )
    second = await svc.create_once(
        owner.id,
        "SLA Breach Alert",
        "Same event",
        category="sla",
        severity="error",
        reference_id="APP-001",
        window_minutes=60,
    )
    assert first.id == second.id
    result = await db_session.execute(select(Notification).where(Notification.user_id == owner.id))
    assert len(result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_notification_center_api_is_owner_scoped(db_session):
    owner, other = await _users(db_session)
    await NotificationService(db_session).create(
        owner.id,
        "Approval Approved",
        "Your approval is complete.",
        category="approval",
        severity="success",
        reference_id="APP-OWN-001",
    )
    await NotificationService(db_session).create(
        other.id,
        "Other User",
        "Private message",
        category="general",
    )

    client = TestClient(app)
    response = client.get("/api/notifications", headers=_headers(owner))
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["unread"] == 1
    assert payload["notifications"][0]["action_path"] == "/dashboard/applications/APP-OWN-001"


@pytest.mark.asyncio
async def test_notification_center_mark_read_and_summary_api(db_session):
    owner, _ = await _users(db_session)
    note = await NotificationService(db_session).create(
        owner.id,
        "Inspection",
        "Inspection scheduled",
        category="inspection",
    )
    client = TestClient(app)
    headers = _headers(owner)
    read = client.post(f"/api/notifications/{note.id}/read", headers=headers)
    assert read.status_code == 200
    assert read.json()["status"] == "read"
    read_again = client.post(f"/api/notifications/{note.id}/read", headers=headers)
    assert read_again.status_code == 200
    summary = client.get("/api/notifications/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["unread"] == 0


@pytest.mark.asyncio
async def test_notification_center_mark_all_read_by_category(db_session):
    owner, _ = await _users(db_session)
    svc = NotificationService(db_session)
    await svc.create(owner.id, "A", "a", category="approval")
    await svc.create(owner.id, "B", "b", category="query")
    client = TestClient(app)
    response = client.post("/api/notifications/read-all?category=approval", headers=_headers(owner))
    assert response.status_code == 200
    assert response.json()["marked"] == 1
    remaining = await svc.list_for_user(owner.id, unread_only=True)
    assert len(remaining) == 1
    assert remaining[0].category == "query"


@pytest.mark.asyncio
async def test_notification_action_path_for_project_categories(db_session):
    owner, _ = await _users(db_session)
    project = Project(user_id=owner.id, name="Project", company_name="Company")
    db_session.add(project)
    await db_session.commit()
    note = await NotificationService(db_session).create(
        owner.id,
        "Renewal due",
        "Renewal",
        category="compliance",
        project_id=project.id,
    )
    assert NotificationService.action_path(note) == f"/dashboard/{project.id}/compliance"

@pytest.mark.asyncio
async def test_notification_action_path_for_regulatory_change(db_session):
    owner, _ = await _users(db_session)
    note = await NotificationService(db_session).create(
        owner.id,
        "Regulatory update",
        "Review change",
        category="regulatory",
        reference_id="00000000-0000-0000-0000-000000000001",
    )
    assert NotificationService.action_path(note) == "/dashboard/regulatory?change=00000000-0000-0000-0000-000000000001"
