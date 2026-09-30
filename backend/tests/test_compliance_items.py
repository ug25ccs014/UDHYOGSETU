"""Regression tests: compliance items are materialized from APPROVED approvals.

Previously ``ComplianceItem`` rows were never written by any workflow, so the
compliance dashboard and score always reported 0 items, zero adherence, and a
zero ``timeliness`` component. The lazy ``ensure_compliance_items`` seeding
fixes that (idempotently) and the dashboard now returns the item list + score
the frontend actually consumes.
"""

import uuid
from datetime import datetime, timedelta

import pytest

from app.models import Approval, ApprovalStatus, Project, User
from app.services.compliance import ComplianceService
from app.services.compliance_tracker import ComplianceTracker


@pytest.fixture
async def approved_project(db_session):
    user = User(
        email=f"ci-{uuid.uuid4().hex[:8]}@example.com",
        name="Compliance User",
        phone="9876503333",
        role="ENTREPRENEUR",
    )
    user.password_hash = "x"
    db_session.add(user)
    await db_session.flush()

    project = Project(user_id=user.id, name="CI Project", company_name="CI Corp")
    db_session.add(project)
    await db_session.flush()

    approved = Approval(
        project_id=project.id,
        name="Factory License",
        department="Industries Department",
        status=ApprovalStatus.APPROVED,
        approved_at=datetime.utcnow() - timedelta(days=30),
        renewal_period_days=360,
    )
    pending = Approval(
        project_id=project.id,
        name="Boiler Registration",
        department="Boiler",
        status=ApprovalStatus.SUBMITTED,
    )
    db_session.add_all([approved, pending])
    await db_session.commit()

    return project


@pytest.mark.asyncio
async def test_approved_approval_seeds_compliance_items(db_session, approved_project):
    """Approved approvals produce persisted compliance requirements."""
    service = ComplianceService(db_session)
    items = await service.get_compliance_items(approved_project.id)

    assert len(items) >= 5  # "Factory License" requirement set
    assert all(i.project_id == approved_project.id for i in items)
    assert all((i.status.value if hasattr(i.status, "value") else i.status) == "ON_TRACK" for i in items)
    assert all(i.next_due is not None for i in items)
    assert all(i.source == "auto-seeded" for i in items)


@pytest.mark.asyncio
async def test_ensure_compliance_items_is_idempotent(db_session, approved_project):
    """Re-running seeding never creates duplicates."""
    service = ComplianceService(db_session)
    await service.ensure_compliance_items(approved_project.id)
    await service.ensure_compliance_items(approved_project.id)

    items = await service.get_compliance_items(approved_project.id)
    keys = {(i.category, i.requirement) for i in items}
    assert len(items) == len(keys)


@pytest.mark.asyncio
async def test_dashboard_returns_items_and_score(db_session, approved_project):
    """Dashboard contract matches the frontend: items list + score, not zero."""
    dashboard = await ComplianceService(db_session).get_compliance_dashboard(approved_project.id)

    assert dashboard["score"] == 100.0
    assert dashboard["overall_score"] == 100.0
    assert len(dashboard["items"]) == dashboard["items_count"] > 0
    assert dashboard["items"][0]["status"] == "ON_TRACK"
    assert "next_due" in dashboard["items"][0]


@pytest.mark.asyncio
async def test_score_uses_materialized_items(db_session, approved_project):
    """Score components now reflect seeded adherence/timeliness."""
    result = await ComplianceTracker(db_session).get_compliance_score(str(approved_project.id))

    assert result["components"]["compliance_adherence"] > 0
    assert result["components"]["timeliness"] > 0
    assert result["score"] > 0


@pytest.mark.asyncio
async def test_no_approvals_yields_empty_safe_dashboard(db_session):
    """A project without approvals returns a well-formed zero dashboard."""
    user = User(
        email=f"ci0-{uuid.uuid4().hex[:8]}@example.com",
        name="Zero Compliance User",
        phone="9876503444",
        role="ENTREPRENEUR",
    )
    user.password_hash = "x"
    db_session.add(user)
    await db_session.flush()

    project = Project(user_id=user.id, name="Empty Project", company_name="Empty Corp")
    db_session.add(project)
    await db_session.commit()

    dashboard = await ComplianceService(db_session).get_compliance_dashboard(project.id)

    assert dashboard["score"] == 0
    assert dashboard["items"] == []
    assert dashboard["items_count"] == 0