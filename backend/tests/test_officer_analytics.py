"""Tests for the officer analytics aggregation."""

import uuid

import pytest

from app.models import Approval, ApprovalStatus, Project, User


@pytest.fixture
async def populated(db_session):
    user = User(
        email=f"off-{uuid.uuid4().hex[:8]}@example.com",
        name="Officer Test",
        phone="9876502222",
        role="ENTREPRENEUR",
    )
    user.password_hash = "x"
    db_session.add(user)
    await db_session.flush()

    project = Project(user_id=user.id, name="P", company_name="C")
    db_session.add(project)
    await db_session.flush()

    db_session.add_all([
        Approval(project_id=project.id, name="A", department="MPCB", estimated_processing_days=30),
        Approval(project_id=project.id, name="B", department="Factory", status=ApprovalStatus.APPROVED, estimated_processing_days=10),
        Approval(project_id=project.id, name="C", department="MPCB", estimated_processing_days=60),
    ])
    await db_session.commit()


@pytest.mark.asyncio
async def test_overview_counts(populated, db_session):
    from app.services.officer_analytics import OfficerAnalyticsService
    svc = OfficerAnalyticsService(db_session)
    overview = await svc.overview()
    assert overview["total_applications"] == 3
    assert overview["approved"] == 1
    assert overview["pending_review"] == 2


@pytest.mark.asyncio
async def test_by_department_aggregates(populated, db_session):
    from app.services.officer_analytics import OfficerAnalyticsService
    svc = OfficerAnalyticsService(db_session)
    departments = await svc.by_department()
    mpcb = [d for d in departments if d["department"] == "MPCB"]
    factory = [d for d in departments if d["department"] == "Factory"]
    assert mpcb and mpcb[0]["total"] == 2 and mpcb[0]["pending"] == 2
    assert factory and factory[0]["approved"] == 1


@pytest.mark.asyncio
async def test_status_distribution(populated, db_session):
    from app.services.officer_analytics import OfficerAnalyticsService
    svc = OfficerAnalyticsService(db_session)
    dist = await svc.status_distribution()
    total = sum(d["count"] for d in dist)
    assert total == 3


@pytest.mark.asyncio
async def test_command_center_includes_live_queue_and_bottlenecks(db_session):
    from datetime import datetime, timedelta, timezone
    from app.services.officer_analytics import OfficerAnalyticsService

    owner = User(
        email=f"cmd-{uuid.uuid4().hex[:8]}@example.com",
        name="Command Owner",
        phone="9876503333",
        password_hash="x",
        role="ENTREPRENEUR",
    )
    db_session.add(owner)
    await db_session.flush()
    project = Project(user_id=owner.id, name="Command Project", company_name="Command Co")
    db_session.add(project)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    db_session.add_all([
        Approval(
            project_id=project.id,
            application_id="CMD-001",
            name="MPCB Consent",
            department="MPCB",
            status=ApprovalStatus.SUBMITTED,
            submitted_at=now - timedelta(days=55),
            estimated_processing_days=60,
        ),
        Approval(
            project_id=project.id,
            application_id="CMD-002",
            name="Factory License",
            department="Factory",
            status=ApprovalStatus.INSPECTION,
            submitted_at=now - timedelta(days=10),
            estimated_processing_days=30,
        ),
    ])
    await db_session.commit()

    data = await OfficerAnalyticsService(db_session).command_center(limit=10)
    assert data["scope"] == "OFFICER"
    assert data["overview"]["review_queue_count"] == 2
    assert data["throughput"]["submissions_7d"] == 0
    assert len(data["priority_queue"]) == 2
    assert any(item["name"] == "Inspection pending" and item["count"] == 1 for item in data["bottlenecks"])
    assert {item["department"] for item in data["departments"]} == {"MPCB", "Factory"}


@pytest.mark.asyncio
async def test_command_center_filters_priority_queue_without_changing_global_metrics(db_session):
    from datetime import datetime, timedelta, timezone
    from app.services.officer_analytics import OfficerAnalyticsService

    owner = User(
        email=f"filter-{uuid.uuid4().hex[:8]}@example.com",
        name="Filter Owner",
        phone="9876503334",
        password_hash="x",
        role="ENTREPRENEUR",
    )
    db_session.add(owner)
    await db_session.flush()
    project = Project(user_id=owner.id, name="Filter Project", company_name="Filter Co")
    db_session.add(project)
    await db_session.flush()
    now = datetime.now(timezone.utc)
    db_session.add_all([
        Approval(project_id=project.id, application_id="F-1", name="MPCB", department="MPCB", status=ApprovalStatus.SUBMITTED, submitted_at=now - timedelta(days=10), estimated_processing_days=60),
        Approval(project_id=project.id, application_id="F-2", name="Factory", department="Factory", status=ApprovalStatus.SUBMITTED, submitted_at=now - timedelta(days=40), estimated_processing_days=60),
    ])
    await db_session.commit()

    data = await OfficerAnalyticsService(db_session).command_center(department="MPCB", limit=10)
    assert data["overview"]["total_applications"] == 2
    assert len(data["priority_queue"]) == 1
    assert data["priority_queue"][0]["department"] == "MPCB"


def test_command_center_endpoint_is_officer_only():
    import asyncio
    from fastapi.testclient import TestClient
    from app.core.database import AsyncSessionLocal
    from app.core.security import create_access_token, hash_password
    from app.main import app
    from app.models import User, UserRole

    async def _seed_and_tokens():
        async with AsyncSessionLocal() as db:
            officer = User(
                email=f"cmd-officer-{uuid.uuid4().hex[:8]}@example.com",
                name="Cmd Officer",
                phone="9876503335",
                password_hash=hash_password("Password@123"),
                role=UserRole.OFFICER,
                is_active=True,
            )
            entrepreneur = User(
                email=f"cmd-ent-{uuid.uuid4().hex[:8]}@example.com",
                name="Cmd Entrepreneur",
                phone="9876503336",
                password_hash=hash_password("Password@123"),
                role=UserRole.ENTREPRENEUR,
                is_active=True,
            )
            db.add_all([officer, entrepreneur])
            await db.commit()
            return (
                create_access_token(data={"sub": str(officer.id), "email": officer.email, "role": "OFFICER"}),
                create_access_token(data={"sub": str(entrepreneur.id), "email": entrepreneur.email, "role": "ENTREPRENEUR"}),
            )

    officer_token, entrepreneur_token = asyncio.run(_seed_and_tokens())
    client = TestClient(app)
    allowed = client.get("/api/officer/command-center", headers={"Authorization": f"Bearer {officer_token}"})
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["scope"] == "OFFICER"

    denied = client.get("/api/officer/command-center", headers={"Authorization": f"Bearer {entrepreneur_token}"})
    assert denied.status_code == 403, denied.text


