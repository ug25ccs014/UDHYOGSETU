"""Tests for Step 8 SLA + Smart Risk orchestration."""

from datetime import datetime, timedelta, timezone
import uuid

import pytest
from sqlalchemy import insert

from app.models import (
    ApplicationQuery,
    Approval,
    ApprovalStatus,
    Document,
    DocumentStatus,
    InspectionVisit,
    InspectionVisitStatus,
    Project,
    User,
    UserRole,
    inspection_visit_approvals,
    approval_documents,
)
from app.services.sla_risk import SlaRiskService


@pytest.mark.asyncio
async def test_enriched_risk_includes_query_inspection_and_document_signals(db_session):
    user = User(
        email=f"risk-{uuid.uuid4().hex[:8]}@example.com",
        name="Risk User",
        phone="9876501234",
        password_hash="x",
        role=UserRole.ENTREPRENEUR,
    )
    db_session.add(user)
    await db_session.flush()

    project = Project(
        user_id=user.id,
        name="Risk Project",
        company_name="Risk Industries",
        location_state="Maharashtra",
        location_district="Pune",
    )
    db_session.add(project)
    await db_session.flush()

    approval = Approval(
        project_id=project.id,
        name="MPCB Consent",
        department="MPCB",
        status=ApprovalStatus.SUBMITTED,
        submitted_at=datetime.now(timezone.utc) - timedelta(days=50),
        estimated_processing_days=60,
        is_mandatory=True,
    )
    db_session.add(approval)
    await db_session.flush()

    query = ApplicationQuery(
        approval_id=approval.id,
        query_fingerprint="a" * 64,
        query_text="Provide ETP details",
        status="OPEN",
    )
    document = Document(
        project_id=project.id,
        file_name="etp-warning.pdf",
        file_path="/tmp/etp-warning.pdf",
        file_type="application/pdf",
        status=DocumentStatus.WARNING,
    )
    db_session.add_all([query, document])
    await db_session.flush()
    await db_session.execute(
        insert(approval_documents).values(approval_id=approval.id, document_id=document.id)
    )

    visit = InspectionVisit(
        project_id=project.id,
        scheduled_start=datetime.now(timezone.utc) + timedelta(days=4),
        scheduled_end=datetime.now(timezone.utc) + timedelta(days=4, minutes=90),
        status=InspectionVisitStatus.SCHEDULED.value,
        location="MIDC Pune",
        checklist=[],
    )
    db_session.add(visit)
    await db_session.flush()
    await db_session.execute(
        insert(inspection_visit_approvals).values(
            inspection_visit_id=visit.id,
            approval_id=approval.id,
        )
    )
    await db_session.commit()

    result = await SlaRiskService(db_session).evaluate_approval(approval, project)

    assert result["predictive_assistance"] is True
    assert result["signals"]["query_open_count"] == 1
    assert result["signals"]["inspection_scheduled"] is True
    assert result["signals"]["document_issue_count"] == 1
    assert result["signals"]["government_source"] == "not_connected"
    assert result["risk_band"] in {"MEDIUM", "HIGH"}
    assert any("query" in item.lower() for item in result["key_risk_factors"])
    assert result["recommended_actions"]
    assert result["project_name"] == "Risk Project"
    assert result["company_name"] == "Risk Industries"
    assert "statutory" in result["disclaimer"].lower()


@pytest.mark.asyncio
async def test_portfolio_is_owner_scoped(db_session):
    owner = User(
        email=f"owner-{uuid.uuid4().hex[:8]}@example.com",
        name="Owner",
        phone="9876501111",
        password_hash="x",
        role=UserRole.ENTREPRENEUR,
    )
    other = User(
        email=f"other-{uuid.uuid4().hex[:8]}@example.com",
        name="Other",
        phone="9876501112",
        password_hash="x",
        role=UserRole.ENTREPRENEUR,
    )
    db_session.add_all([owner, other])
    await db_session.flush()

    p1 = Project(user_id=owner.id, name="P1", company_name="C1")
    p2 = Project(user_id=other.id, name="P2", company_name="C2")
    db_session.add_all([p1, p2])
    await db_session.flush()
    db_session.add_all([
        Approval(project_id=p1.id, name="A1", department="MPCB", status=ApprovalStatus.SUBMITTED, estimated_processing_days=30),
        Approval(project_id=p2.id, name="A2", department="Fire", status=ApprovalStatus.SUBMITTED, estimated_processing_days=30),
    ])
    await db_session.commit()

    result = await SlaRiskService(db_session).portfolio(owner.id)

    assert result["total_applications"] == 1
    assert result["applications"][0]["approval_name"] == "A1"


@pytest.mark.asyncio
async def test_officer_queue_excludes_terminal_applications_and_filters_risk(db_session):
    user = User(
        email=f"officer-owner-{uuid.uuid4().hex[:8]}@example.com",
        name="Owner",
        phone="9876502222",
        password_hash="x",
        role=UserRole.ENTREPRENEUR,
    )
    db_session.add(user)
    await db_session.flush()
    project = Project(user_id=user.id, name="Officer Project", company_name="Officer Co")
    db_session.add(project)
    await db_session.flush()

    db_session.add_all([
        Approval(
            project_id=project.id,
            name="Approved App",
            department="MPCB",
            status=ApprovalStatus.APPROVED,
            estimated_processing_days=30,
            submitted_at=datetime.now(timezone.utc) - timedelta(days=40),
        ),
        Approval(
            project_id=project.id,
            name="Breached App",
            department="MPCB",
            status=ApprovalStatus.SUBMITTED,
            estimated_processing_days=10,
            submitted_at=datetime.now(timezone.utc) - timedelta(days=30),
        ),
        Approval(
            project_id=project.id,
            name="On Track App",
            department="GST",
            status=ApprovalStatus.SUBMITTED,
            estimated_processing_days=60,
            submitted_at=datetime.now(timezone.utc) - timedelta(days=2),
        ),
    ])
    await db_session.commit()

    service = SlaRiskService(db_session)
    queue = await service.officer_queue(limit=10)
    assert queue["total_applications"] == 2
    assert all(item["status"] not in {"APPROVED", "REJECTED", "EXPIRED", "CANCELED"} for item in queue["applications"])
    assert queue["applications"][0]["approval_name"] == "Breached App"
    assert queue["sla_breached"] == 1

    filtered = await service.officer_queue(risk_band="HIGH", limit=10)
    assert all(item["risk_band"] == "HIGH" for item in filtered["applications"])
    assert any(item["approval_name"] == "Breached App" for item in filtered["applications"])


@pytest.mark.asyncio
async def test_risk_views_ignore_pre_submission_states(db_session):
    user = User(
        email=f"draft-risk-{uuid.uuid4().hex[:8]}@example.com",
        name="Draft User",
        phone="9876503333",
        password_hash="x",
        role=UserRole.ENTREPRENEUR,
    )
    db_session.add(user)
    await db_session.flush()
    project = Project(user_id=user.id, name="Draft Project", company_name="Draft Co")
    db_session.add(project)
    await db_session.flush()
    db_session.add_all([
        Approval(project_id=project.id, name="Draft App", department="MPCB", status=ApprovalStatus.DRAFT, estimated_processing_days=30),
        Approval(project_id=project.id, name="Not Started App", department="Fire", status=ApprovalStatus.NOT_STARTED, estimated_processing_days=20),
    ])
    await db_session.commit()

    result = await SlaRiskService(db_session).portfolio(user.id)

    assert result["total_applications"] == 0
    assert result["applications"] == []
