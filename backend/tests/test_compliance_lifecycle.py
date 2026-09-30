"""Regression tests for the Step-13 compliance and renewal lifecycle."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models import Approval, ApprovalStatus, ComplianceItem, ComplianceStatus, Project, User
from app.services.compliance_lifecycle import ComplianceLifecycleService


@pytest.fixture
async def lifecycle_project(db_session):
    user = User(
        email=f"lifecycle-{uuid.uuid4().hex[:8]}@example.com",
        name="Lifecycle User",
        phone="9876501234",
        role="ENTREPRENEUR",
    )
    user.password_hash = "x"
    db_session.add(user)
    await db_session.flush()
    project = Project(
        user_id=user.id,
        name="Lifecycle Project",
        company_name="Lifecycle Corp",
        industry="Textile",
        sector="Textile",
    )
    db_session.add(project)
    await db_session.flush()
    approval = Approval(
        project_id=project.id,
        name="Factory License",
        department="Department of Factory",
        status=ApprovalStatus.APPROVED,
        approved_at=datetime.now(timezone.utc) - timedelta(days=330),
        renewal_period_days=365,
    )
    db_session.add(approval)
    await db_session.commit()
    return user, project, approval


@pytest.mark.asyncio
async def test_dashboard_materializes_frequency_and_due_state(db_session, lifecycle_project):
    _user, project, _approval = lifecycle_project
    dashboard = await ComplianceLifecycleService(db_session).dashboard(project.id, _user.id)

    assert dashboard["summary"]["total"] >= 5
    assert all(item["frequency"] for item in dashboard["items"])
    assert dashboard["score"] <= 100
    assert isinstance(dashboard["renewals"], list)


@pytest.mark.asyncio
async def test_complete_compliance_item_reschedules_recurring_task(db_session, lifecycle_project):
    user, project, _approval = lifecycle_project
    service = ComplianceLifecycleService(db_session)
    await service.dashboard(project.id, user.id)
    item = (await db_session.execute(
        __import__("sqlalchemy").select(ComplianceItem).where(ComplianceItem.project_id == project.id)
    )).scalars().first()
    before = item.next_due

    payload = await service.complete_item(item.id, user.id)
    assert payload["status"] == ComplianceStatus.ON_TRACK.value
    assert payload["last_completed"] is not None
    assert payload["next_due"] is not None
    assert datetime.fromisoformat(payload["next_due"]) > before


@pytest.mark.asyncio
async def test_renewal_case_is_separate_from_original_approval(db_session, lifecycle_project):
    user, project, approval = lifecycle_project
    service = ComplianceLifecycleService(db_session)
    renewals = await service.list_renewals(project.id, user.id)
    assert len(renewals) == 1
    assert renewals[0]["lifecycle_status"] == "DUE_SOON"

    case = await service.prepare_renewal(project.id, approval.id, user.id)
    assert case["id"]
    assert case["status"] == "PREPARING"
    assert case["approval_id"] == str(approval.id)
    assert case["transparency"]

    detail = await service.renewal_detail(uuid.UUID(case["id"]), user.id)
    assert detail["status"] == "PREPARING"

    approval_result = await db_session.execute(__import__("sqlalchemy").select(Approval).where(Approval.id == approval.id))
    original = approval_result.scalar_one()
    assert original.status == ApprovalStatus.APPROVED


@pytest.mark.asyncio
async def test_renewal_submission_is_explicitly_external(db_session, lifecycle_project):
    user, project, approval = lifecycle_project
    service = ComplianceLifecycleService(db_session)
    case = await service.prepare_renewal(project.id, approval.id, user.id)

    case = await service.update_renewal(uuid.UUID(case["id"]), user.id, status="READY_FOR_SUBMISSION")
    assert case["status"] == "READY_FOR_SUBMISSION"
    case = await service.update_renewal(
        uuid.UUID(case["id"]),
        user.id,
        status="SUBMITTED_EXTERNALLY",
        external_reference="EXT-123",
    )
    assert case["status"] == "SUBMITTED_EXTERNALLY"
    assert case["external_reference"] == "EXT-123"
    assert "No government renewal submission" in case["transparency"]


@pytest.mark.asyncio
async def test_renewal_owner_isolation(db_session, lifecycle_project):
    _user, project, approval = lifecycle_project
    service = ComplianceLifecycleService(db_session)
    case = await service.prepare_renewal(project.id, approval.id, _user.id)

    outsider = User(
        email=f"outsider-{uuid.uuid4().hex[:8]}@example.com",
        name="Outsider",
        phone="9876509999",
        role="ENTREPRENEUR",
    )
    outsider.password_hash = "x"
    db_session.add(outsider)
    await db_session.commit()

    with pytest.raises(ValueError, match="Not authorized"):
        await service.renewal_detail(uuid.UUID(case["id"]), outsider.id)
