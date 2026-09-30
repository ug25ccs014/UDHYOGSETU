"""Regression tests for the compliance-scoring + scenario-simulation fixes.

Covers two audit findings that previously crashed or silently mis-scored:

- ``ComplianceTracker.get_compliance_score`` hit ``Approval.custom_metadata``
  (an attribute that does not exist) -> 500, and enum-vs-string comparisons
  (``status == "APPROVED"``) were always False, so the approval-status score
  was always 0 and alerts were never produced.
- ``ComplianceService.get_compliance_dashboard`` compared ``item.status``
  against a plain string, so ``overall_score`` was always 0.
- ``ScenarioSimulator.simulate_location_change`` was fed a plain state string
  (``project.location_state``) where a dict was expected -> 500.
"""

import uuid
from datetime import datetime, timedelta

import pytest

from app.models import (
    Approval,
    ApprovalStatus,
    ComplianceItem,
    ComplianceStatus,
    Project,
    User,
)


@pytest.fixture
async def project_with_approvals(db_session):
    user = User(
        email=f"score-{uuid.uuid4().hex[:8]}@example.com",
        name="Score User",
        phone="9876502222",
        role="ENTREPRENEUR",
    )
    user.password_hash = "x"
    db_session.add(user)
    await db_session.flush()

    project = Project(user_id=user.id, name="Score Project", company_name="Score Corp")
    db_session.add(project)
    await db_session.flush()

    return user, project


@pytest.mark.asyncio
async def test_compliance_score_no_500_and_status_scored(db_session, project_with_approvals):
    """Score endpoint regressions: no crash, approval status contributes > 0."""
    from app.services.compliance_tracker import ComplianceTracker

    _user, project = project_with_approvals

    approved = Approval(
        project_id=project.id,
        name="Consent to Establish",
        department="MPCB",
        status=ApprovalStatus.APPROVED,
        approved_at=datetime.utcnow() - timedelta(days=100),
        renewal_period_days=360,
    )
    in_progress = Approval(
        project_id=project.id,
        name="Fire No Objection Certificate",
        department="Fire Services",
        status=ApprovalStatus.SUBMITTED,
    )
    db_session.add_all([approved, in_progress])
    await db_session.commit()

    result = await ComplianceTracker(db_session).get_compliance_score(str(project.id))

    assert result["score"] is not None
    assert 0 <= result["score"] <= 100
    assert result["components"]["approval_status"] == 50.0
    assert "grade" in result


@pytest.mark.asyncio
async def test_compliance_alerts_include_approved_near_renewal(db_session, project_with_approvals):
    """Enum-vs-string fix: APPROVED approvals (and not others) surface alerts."""
    from app.services.compliance_tracker import ComplianceTracker

    _user, project = project_with_approvals

    due = Approval(
        project_id=project.id,
        name="Municipal Approval",
        department="Municipal Corporation",
        status=ApprovalStatus.APPROVED,
        approved_at=datetime.utcnow() - timedelta(days=330),
    )
    fresh = Approval(
        project_id=project.id,
        name="State Profile Registration",
        department="Industries Department",
        status=ApprovalStatus.APPROVED,
        approved_at=datetime.utcnow(),
    )
    never = Approval(
        project_id=project.id,
        name="MPCB Consent",
        department="MPCB",
        status=ApprovalStatus.NOT_STARTED,
    )
    db_session.add_all([due, fresh, never])
    await db_session.commit()

    alerts = await ComplianceTracker(db_session).get_compliance_alerts(str(project.id))

    assert any(a["approval_name"] == "Municipal Approval" for a in alerts)
    assert not any(a["approval_name"] == "MPCB Consent" for a in alerts)


@pytest.mark.asyncio
async def test_compliance_dashboard_scores_enum_status(db_session, project_with_approvals):
    """Dashboard no longer always zeros: compliant fraction is reflected."""
    from app.services.compliance import ComplianceService

    _user, project = project_with_approvals

    on_track = ComplianceItem(
        project_id=project.id,
        category="Environmental",
        requirement="Quarterly emission monitoring",
        status=ComplianceStatus.ON_TRACK,
    )
    overdue = ComplianceItem(
        project_id=project.id,
        category="Environmental",
        requirement="Annual environmental audit",
        status=ComplianceStatus.OVERDUE,
    )
    db_session.add_all([on_track, overdue])
    await db_session.commit()

    dashboard = await ComplianceService(db_session).get_compliance_dashboard(project.id)

    assert dashboard["overall_score"] == 50.0
    assert dashboard["categories"]["Environmental"] == {"total": 2, "compliant": 1}
    assert dashboard["items_count"] == 2


@pytest.mark.asyncio
async def test_location_simulation_accepts_plain_state_string(db_session):
    """Scenario simulator survives a string location (business_intelligence pass-through)."""
    from app.services.scenario_simulator import ScenarioSimulator

    simulator = ScenarioSimulator()
    impact = simulator.simulate_location_change(
        {"sector": "Textile", "investment": 5000000, "location": "Maharashtra"},
        {"name": "Surat, Gujarat", "state": "Gujarat"},
    )

    assert isinstance(impact, dict)
    assert impact["scenario"] == "location_change"
    assert "changes" in impact
    assert impact["original_location"] == "Maharashtra"