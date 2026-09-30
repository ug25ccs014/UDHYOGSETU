"""Regression tests for the Step 10 unified project command center."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert

from app.core.security import create_access_token, hash_password
from app.main import app
from app.models import (
    ApplicationQuery,
    Approval,
    ApprovalStatus,
    BusinessProfile,
    Document,
    DocumentStatus,
    Grievance,
    GrievanceEvent,
    InspectionVisit,
    InspectionVisitStatus,
    Project,
    User,
    UserRole,
    inspection_visit_approvals,
)
from app.services.command_center import CommandCenterService


async def _make_project(db):
    owner = User(
        id=uuid.uuid4(),
        email=f"cc-{uuid.uuid4().hex[:8]}@example.com",
        name="Command Center Owner",
        phone="9876504444",
        password_hash=hash_password("Password@123"),
        role=UserRole.ENTREPRENEUR,
    )
    other = User(
        id=uuid.uuid4(),
        email=f"cc-other-{uuid.uuid4().hex[:8]}@example.com",
        name="Other Owner",
        phone="9876504445",
        password_hash=hash_password("Password@123"),
        role=UserRole.ENTREPRENEUR,
    )
    db.add_all([owner, other])
    await db.flush()

    project = Project(
        id=uuid.uuid4(),
        user_id=owner.id,
        name="ABC Textiles",
        company_name="ABC Textiles Pvt Ltd",
        business_type="Manufacturing",
        industry="Textile",
        sector="Textile",
        project_stage="Construction",
        investment_amount=20_000_000,
        location_state="Maharashtra",
        location_district="Pune",
        location_city="Pune",
        employees=50,
        production_type="Dyeing",
        hazardous_materials=False,
        has_boiler=True,
        pollution_potential="High",
        building_type="Industrial",
    )
    other_project = Project(
        user_id=other.id,
        name="Other Project",
        company_name="Other Co",
    )
    profile = BusinessProfile(
        user_id=owner.id,
        company_name="ABC Textiles Pvt Ltd",
        business_type="Manufacturing",
        industry="Textile",
        sector="Textile",
        pan="ABCDE1234F",
        gstin="27ABCDE1234F1Z5",
        udyam_number="UDYAM-MH-01-0000001",
        registered_address="MIDC Pune",
        registered_state="Maharashtra",
        registered_district="Pune",
        registered_city="Pune",
    )
    db.add_all([project, other_project, profile])
    await db.flush()
    return owner, other, project, other_project, profile


@pytest.mark.asyncio
async def test_command_center_composes_all_project_domains(db_session):
    owner, _other, project, _other_project, _profile = await _make_project(db_session)

    draft = Approval(
        project_id=project.id,
        application_id="FACTORY-CC-001",
        name="Factory License",
        department="Department of Factory",
        status=ApprovalStatus.DRAFT,
        estimated_processing_days=30,
        is_mandatory=True,
    )
    breached = Approval(
        project_id=project.id,
        application_id="MPCB-CC-002",
        name="MPCB Consent",
        department="MPCB",
        status=ApprovalStatus.SUBMITTED,
        submitted_at=datetime.now(timezone.utc) - timedelta(days=100),
        estimated_processing_days=60,
        is_mandatory=True,
    )
    approved = Approval(
        project_id=project.id,
        application_id="FIRE-CC-003",
        name="Fire No Objection Certificate",
        department="Fire Services Department",
        status=ApprovalStatus.APPROVED,
        approved_at=datetime.now(timezone.utc) - timedelta(days=20),
        estimated_processing_days=20,
    )
    db_session.add_all([draft, breached, approved])
    await db_session.flush()

    warning_doc = Document(
        project_id=project.id,
        file_name="factory-layout.pdf",
        file_path="demo/factory-layout.pdf",
        file_type="application/pdf",
        status=DocumentStatus.WARNING,
        custom_metadata={"document_type": "FACTORY PLAN"},
    )
    db_session.add(warning_doc)
    await db_session.flush()

    query = ApplicationQuery(
        approval_id=breached.id,
        query_fingerprint="c" * 64,
        query_text="Provide additional ETP capacity details",
        status="OPEN",
    )
    db_session.add(query)
    await db_session.flush()

    visit = InspectionVisit(
        project_id=project.id,
        scheduled_start=datetime.now(timezone.utc) + timedelta(days=2),
        scheduled_end=datetime.now(timezone.utc) + timedelta(days=2, hours=1),
        status=InspectionVisitStatus.SCHEDULED.value,
        location="MIDC Pune",
        checklist=[],
    )
    db_session.add(visit)
    await db_session.flush()
    await db_session.execute(
        insert(inspection_visit_approvals).values(
            inspection_visit_id=visit.id,
            approval_id=breached.id,
        )
    )

    grievance = Grievance(
        user_id=owner.id,
        project_id=project.id,
        approval_id=breached.id,
        application_id=breached.application_id,
        department=breached.department,
        category="SLA Concern",
        subject="MPCB delay follow-up",
        description="Please review the delayed application.",
        priority="HIGH",
        status="ESCALATED",
        escalation_level=1,
        response_target_at=datetime.utcnow() - timedelta(days=1),
    )
    db_session.add(grievance)
    await db_session.flush()
    db_session.add(
        GrievanceEvent(
            grievance_id=grievance.id,
            actor_user_id=owner.id,
            event_type="ESCALATED",
            from_status="IN_REVIEW",
            to_status="ESCALATED",
            note="Demo escalation",
        )
    )
    await db_session.commit()

    result = await CommandCenterService(db_session).build(project.id, owner.id)

    assert result["project"]["company_name"] == "ABC Textiles Pvt Ltd"
    assert result["overview"]["approval_count"] == 3
    assert result["overview"]["high_risk"] >= 1
    assert result["overview"]["sla_breached"] >= 1
    assert result["overview"]["queries"] == 1
    assert result["overview"]["inspections"] == 1
    assert result["overview"]["documents_attention"] == 1
    assert result["overview"]["compliance_score"] == 100
    assert result["overview"]["open_grievances"] == 1
    assert result["roadmap"]["total_count"] == 3
    assert result["incentives"]["count"] >= 0
    assert any(action["priority"] == "HIGH" for action in result["action_center"])
    assert any("query" in action["title"].lower() for action in result["action_center"])
    assert result["metadata"]["government_api_status"] == "not_connected"
    assert "statutory" in result["metadata"]["disclaimer"].lower()


@pytest.mark.asyncio
async def test_command_center_owner_isolation(db_session):
    owner, other, project, other_project, _profile = await _make_project(db_session)
    db_session.add(
        Approval(
            project_id=project.id,
            name="Owner Approval",
            department="MPCB",
            status=ApprovalStatus.DRAFT,
            estimated_processing_days=30,
        )
    )
    await db_session.commit()

    owner_result = await CommandCenterService(db_session).build(project.id, owner.id)
    assert owner_result["project"]["name"] == "ABC Textiles"

    with pytest.raises(ValueError):
        await CommandCenterService(db_session).build(other_project.id, owner.id)

    with pytest.raises(ValueError):
        await CommandCenterService(db_session).build(project.id, other.id)


@pytest.mark.asyncio
async def test_command_center_http_route_is_owner_scoped(db_session):
    owner, other, project, _other_project, _profile = await _make_project(db_session)
    await db_session.commit()

    owner_token = create_access_token({"sub": str(owner.id), "email": owner.email, "role": "ENTREPRENEUR"})
    other_token = create_access_token({"sub": str(other.id), "email": other.email, "role": "ENTREPRENEUR"})
    client = TestClient(app)

    response = client.get(
        f"/api/command-center/projects/{project.id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["project"]["id"] == str(project.id)
    assert "action_center" in body

    forbidden = client.get(
        f"/api/command-center/projects/{project.id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert forbidden.status_code == 403

    missing = client.get(
        f"/api/command-center/projects/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert missing.status_code == 403
