"""Tests for the in-app notifications engine."""

import uuid

import pytest

from app.models import User


@pytest.fixture
async def test_user(db_session):
    user = User(
        email=f"user-{uuid.uuid4().hex[:8]}@example.com",
        name="Notify User",
        phone="9876501234",
        role="ENTREPRENEUR",
    )
    user.password_hash = "not-used"
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_create_and_list_notification(db_session, test_user):
    from app.notifications.service import NotificationService
    svc = NotificationService(db_session)
    n = await svc.create(
        test_user.id,
        "Approval Approved",
        "Your consent is approved.",
        category="approval",
        severity="success",
    )
    assert n.is_read is False

    rows = await svc.list_for_user(test_user.id)
    assert len(rows) == 1
    assert rows[0].title == "Approval Approved"

    count = await svc.unread_count(test_user.id)
    assert count == 1


@pytest.mark.asyncio
async def test_mark_read(db_session, test_user):
    from app.notifications.service import NotificationService
    svc = NotificationService(db_session)
    n = await svc.create(test_user.id, "Hi", "msg")
    ok = await svc.mark_read(test_user.id, n.id)
    assert ok is True
    assert await svc.unread_count(test_user.id) == 0


@pytest.mark.asyncio
async def test_notification_dict_roundtrip(db_session, test_user):
    from app.notifications.service import NotificationService
    svc = NotificationService(db_session)
    n = await svc.create(test_user.id, "Title", "Body")
    d = n.to_dict()
    assert d["title"] == "Title"
    assert d["is_read"] is False
    assert d["id"] == str(n.id)