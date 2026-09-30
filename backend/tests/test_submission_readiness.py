"""Regression coverage for the pre-submission readiness engine."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import insert, select

from app.models import (
    Approval,
    ApprovalRule,
    BusinessProfile,
    Document,
    DocumentStatus,
    GovernmentService,
    Project,
    User,
    UserRole,
    approval_documents,
    business_profile_documents,
)
from app.services.submission_readiness import SubmissionReadinessService


@pytest.mark.asyncio
async def test_readiness_reports_missing_documents_as_blockers(db_session):
    user = User(
        email=f"ready-{uuid.uuid4().hex[:8]}@example.com",
        name="Readiness User",
        phone="9876543210",
        password_hash="unused",
        role=UserRole.ENTREPRENEUR,
    )
    db_session.add(user)
    await db_session.flush()
    project = Project(
        user_id=user.id,
        name="Factory",
        company_name="ABC Textiles Pvt Ltd",
        business_type="manufacturing",
        industry="Textile",
        sector="Textile",
        project_stage="implementation",
        location_state="Maharashtra",
        location_district="Pune",
    )
    db_session.add(project)
    rule = ApprovalRule(
        name="Fire Readiness Rule",
        department="Fire Services Department",
        conditions={"type": "COMPARISON", "field": "employees", "operator": "greater_than", "value": 9},
        required_documents=["Building Layout", "Fire Safety Plan"],
    )
    db_session.add(rule)
    await db_session.flush()
    approval = Approval(
        project_id=project.id,
        name=rule.name,
        department=rule.department,
        status="DRAFT",
    )
    db_session.add(approval)
    profile = BusinessProfile(
        user_id=user.id,
        company_name="ABC Textiles Pvt Ltd",
        business_type="manufacturing",
        industry="Textile",
        sector="Textile",
        registered_address="Pune Industrial Area",
        registered_state="Maharashtra",
        registered_district="Pune",
        registered_city="Pune",
    )
    db_session.add(profile)
    await db_session.commit()

    result = await SubmissionReadinessService(db_session).evaluate(approval.id, user.id)

    assert result["can_submit"] is False
    assert result["readiness_state"] == "BLOCKED"
    assert result["summary"]["documents_missing"] == 2
    assert {item["status"] for item in result["document_checklist"]} == {"MISSING"}


@pytest.mark.asyncio
async def test_readiness_surfaces_matching_unattached_project_document(db_session):
    user = User(
        email=f"ready-{uuid.uuid4().hex[:8]}@example.com",
        name="Candidate User",
        phone="9876543210",
        password_hash="unused",
        role=UserRole.ENTREPRENEUR,
    )
    db_session.add(user)
    await db_session.flush()
    project = Project(
        user_id=user.id,
        name="Factory",
        company_name="ABC Textiles Pvt Ltd",
        business_type="manufacturing",
        industry="Textile",
        sector="Textile",
        project_stage="implementation",
    )
    db_session.add(project)
    rule = ApprovalRule(
        name="Candidate Rule",
        department="Fire Services Department",
        conditions={},
        required_documents=["Building Layout"],
    )
    db_session.add(rule)
    await db_session.flush()
    approval = Approval(
        project_id=project.id,
        name=rule.name,
        department=rule.department,
        status="DRAFT",
    )
    db_session.add(approval)
    document = Document(
        project_id=project.id,
        file_name="factory_building_layout.pdf",
        file_path="/tmp/factory_building_layout.pdf",
        file_type="application/pdf",
        status=DocumentStatus.VERIFIED,
        extracted_fields={"document_type": "BUILDING LAYOUT", "name": "ABC Textiles Pvt Ltd"},
        validation_errors=[],
    )
    db_session.add(document)
    await db_session.commit()

    result = await SubmissionReadinessService(db_session).evaluate(approval.id, user.id)
    item = result["document_checklist"][0]

    assert item["status"] == "MISSING"
    assert item["candidate_documents"]
    assert item["candidate_documents"][0]["document_id"] == str(document.id)



@pytest.mark.asyncio
async def test_readiness_is_ready_with_matching_valid_documents(db_session):
    user = User(
        email=f"ready-{uuid.uuid4().hex[:8]}@example.com",
        name="Ready User",
        phone="9876543210",
        password_hash="unused",
        role=UserRole.ENTREPRENEUR,
    )
    db_session.add(user)
    await db_session.flush()
    project = Project(
        user_id=user.id,
        name="Factory",
        company_name="ABC Textiles Pvt Ltd",
        business_type="manufacturing",
        industry="Textile",
        sector="Textile",
        project_stage="implementation",
        location_state="Maharashtra",
        location_district="Pune",
    )
    db_session.add(project)
    rule = ApprovalRule(
        name="Fire Readiness Rule",
        department="Fire Services Department",
        conditions={},
        required_documents=["Building Layout", "Fire Safety Plan"],
    )
    db_session.add(rule)
    await db_session.flush()
    approval = Approval(
        project_id=project.id,
        name=rule.name,
        department=rule.department,
        status="DRAFT",
    )
    db_session.add(approval)
    profile = BusinessProfile(
        user_id=user.id,
        company_name="ABC Textiles Pvt Ltd",
        business_type="manufacturing",
        industry="Textile",
        sector="Textile",
        registered_address="Pune Industrial Area",
        registered_state="Maharashtra",
        registered_district="Pune",
        registered_city="Pune",
        pan="ABCDE1234F",
        gstin="27ABCDE1234F1Z5",
    )
    db_session.add(profile)
    docs = [
        Document(
            project_id=project.id,
            file_name="building_layout.pdf",
            file_path="/tmp/building_layout.pdf",
            file_type="application/pdf",
            status=DocumentStatus.VERIFIED,
            extracted_fields={"document_type": "BUILDING LAYOUT", "name": "ABC Textiles Pvt Ltd"},
            validation_errors=[],
        ),
        Document(
            project_id=project.id,
            file_name="fire_safety_plan.pdf",
            file_path="/tmp/fire_safety_plan.pdf",
            file_type="application/pdf",
            status=DocumentStatus.VERIFIED,
            extracted_fields={"document_type": "FIRE SAFETY PLAN", "name": "ABC Textiles Pvt Ltd"},
            validation_errors=[],
        ),
    ]
    db_session.add_all(docs)
    await db_session.flush()
    await db_session.execute(insert(approval_documents), [{"approval_id": approval.id, "document_id": d.id} for d in docs])
    await db_session.commit()

    result = await SubmissionReadinessService(db_session).evaluate(approval.id, user.id)

    assert result["can_submit"] is True
    assert result["readiness_state"] == "READY"
    assert result["summary"]["documents_ready"] == 2
    assert result["summary"]["blockers"] == 0


@pytest.mark.asyncio
async def test_readiness_blocks_invalid_document_and_detects_profile_mismatch(db_session):
    user = User(
        email=f"ready-{uuid.uuid4().hex[:8]}@example.com",
        name="Mismatch User",
        phone="9876543210",
        password_hash="unused",
        role=UserRole.ENTREPRENEUR,
    )
    db_session.add(user)
    await db_session.flush()
    project = Project(
        user_id=user.id,
        name="Factory",
        company_name="ABC Textiles Pvt Ltd",
        business_type="manufacturing",
        industry="Textile",
        sector="Textile",
        project_stage="implementation",
        location_state="Maharashtra",
        location_district="Pune",
    )
    db_session.add(project)
    rule = ApprovalRule(
        name="GST Readiness Rule",
        department="GST Department",
        conditions={},
        required_documents=["PAN Card"],
    )
    db_session.add(rule)
    await db_session.flush()
    approval = Approval(
        project_id=project.id,
        name=rule.name,
        department=rule.department,
        status="DRAFT",
    )
    db_session.add(approval)
    profile = BusinessProfile(
        user_id=user.id,
        company_name="XYZ Industries Pvt Ltd",
        business_type="manufacturing",
        industry="Textile",
        sector="Textile",
        registered_address="Pune",
        registered_state="Maharashtra",
        registered_district="Pune",
        registered_city="Pune",
        pan="ABCDE1234F",
    )
    db_session.add(profile)
    doc = Document(
        project_id=project.id,
        file_name="pan_card.pdf",
        file_path="/tmp/pan_card.pdf",
        file_type="application/pdf",
        status=DocumentStatus.WARNING,
        extracted_fields={
            "document_type": "PAN CARD",
            "name": "ABC Textiles Pvt Ltd",
            "pan": "ZZZZZ9999Z",
        },
        validation_errors=["Invalid PAN format: ZZZZZ9999Z"],
    )
    db_session.add(doc)
    await db_session.flush()
    await db_session.execute(insert(approval_documents).values(approval_id=approval.id, document_id=doc.id))
    await db_session.commit()

    result = await SubmissionReadinessService(db_session).evaluate(approval.id, user.id)

    codes = {issue["code"] for issue in result["blocking_issues"]}
    assert "DOCUMENT_INVALID" in codes or "CROSS_DOCUMENT_PAN" in codes
    assert "PROFILE_PROJECT_NAME_MISMATCH" in codes
    assert result["can_submit"] is False


@pytest.mark.asyncio
async def test_readiness_does_not_expose_another_users_application(db_session):
    first = User(
        email=f"ready-{uuid.uuid4().hex[:8]}@example.com",
        name="First",
        phone="9876543210",
        password_hash="unused",
        role=UserRole.ENTREPRENEUR,
    )
    second = User(
        email=f"ready-{uuid.uuid4().hex[:8]}@example.com",
        name="Second",
        phone="9876543211",
        password_hash="unused",
        role=UserRole.ENTREPRENEUR,
    )
    db_session.add_all([first, second])
    await db_session.flush()
    project = Project(user_id=first.id, name="Private", company_name="Private Co")
    db_session.add(project)
    await db_session.flush()
    approval = Approval(project_id=project.id, name="Private", department="Test", status="DRAFT")
    db_session.add(approval)
    await db_session.commit()

    with pytest.raises(ValueError):
        await SubmissionReadinessService(db_session).evaluate(approval.id, second.id)
