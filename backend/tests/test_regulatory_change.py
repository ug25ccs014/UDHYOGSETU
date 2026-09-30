"""Tests for regulatory change center analysis."""

from datetime import datetime, timedelta, timezone
import uuid

from app.models import Approval, ApprovalStatus, KnowledgeDocument, Project, User, UserRole
from app.services.regulatory_change import RegulatoryChangeService


async def _make_doc(db, **kwargs):
    doc = KnowledgeDocument(
        title=kwargs.get("title", "Boiler Regulations"),
        department=kwargs.get("department", "boiler"),
        version=kwargs.get("version", "1.0"),
        is_latest=kwargs.get("is_latest", True),
        text=kwargs.get("text", "Rule text."),
        document_type="regulation",
        supersedes_document_id=kwargs.get("supersedes_document_id"),
        effective_date=kwargs.get("effective_date"),
        effective_to=kwargs.get("effective_to"),
        source_url=kwargs.get("source_url"),
        sector=kwargs.get("sector"),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def _make_project_and_approval(db, department="boiler", sector="Textile"):
    user = User(
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        name="Applicant",
        phone="9999999999",
        password_hash="hash",
        role=UserRole.ENTREPRENEUR,
    )
    db.add(user)
    await db.flush()
    project = Project(
        user_id=user.id,
        name="Demo Project",
        company_name="Demo Industries",
        industry="Textile",
        sector=sector,
        location_state="Maharashtra",
        location_district="Nashik",
    )
    db.add(project)
    await db.flush()
    approval = Approval(
        project_id=project.id,
        name="Boiler Registration",
        department=department,
        sector=sector,
        status=ApprovalStatus.UNDER_REVIEW,
        is_active=True,
    )
    db.add(approval)
    await db.commit()
    return user, project, approval


async def test_diff_detects_changed_fields_and_section_changes(db_session):
    old = await _make_doc(
        db_session,
        title="Boiler Regulations 2024",
        version="2024",
        text="# Applicability\nOld boiler safety provision.\n\n# Documents\nCertificate required.",
        effective_date=datetime(2024, 1, 1),
    )
    new = await _make_doc(
        db_session,
        title="Boiler Regulations 2026",
        version="2026",
        supersedes_document_id=old.id,
        text="# Applicability\nNew boiler safety provision.\n\n# Documents\nCertificate required.\n\n# Inspection\nAnnual inspection details required.",
        effective_date=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=10),
        source_url="https://example.gov/regulation",
    )

    result = await RegulatoryChangeService(db_session).diff(new.id)
    assert result["title"] == "Boiler Regulations 2026"
    assert result["supersedes_version"] == "2024"
    assert any(c["field"] == "title" for c in result["changed_fields"])
    assert result["text_changed"] is True
    assert result["effective_status"] == "ACTIVE"
    assert result["source"]["url"] == "https://example.gov/regulation"
    assert any(item["type"] == "ADDED" for item in result["change_items"])
    assert result["note"]


async def test_recent_changes_includes_impact_and_effective_state(db_session):
    _, project, _ = await _make_project_and_approval(db_session)
    old = await _make_doc(
        db_session,
        department="boiler",
        version="v1",
        text="# Rules\nBaseline",
        effective_date=datetime(2025, 1, 1),
    )
    new = await _make_doc(
        db_session,
        department="boiler",
        version="v2",
        supersedes_document_id=old.id,
        text="# Rules\nUpdated",
        effective_date=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1),
    )

    changes = await RegulatoryChangeService(db_session).recent_changes()
    match = next(change for change in changes if change["document_id"] == str(new.id))
    assert match["effective_status"] == "ACTIVE"
    assert match["impact"]["potentially_affected"] is True
    assert match["impact"]["approval_count"] == 1
    assert match["impact"]["project_count"] == 1

    project_changes = await RegulatoryChangeService(db_session).project_changes(project.id)
    assert any(change["document_id"] == str(new.id) for change in project_changes)


async def test_project_impact_does_not_leak_other_project_names(db_session):
    _, project, _ = await _make_project_and_approval(db_session)
    await _make_project_and_approval(db_session, department="boiler", sector="Chemicals")
    old = await _make_doc(db_session, department="boiler", version="v1", text="# Rules\nBaseline")
    new = await _make_doc(
        db_session,
        department="boiler",
        version="v2",
        supersedes_document_id=old.id,
        text="# Rules\nUpdated",
    )

    result = await RegulatoryChangeService(db_session).diff(new.id, project_id=project.id)
    current_project = result["impact"]["current_project"]
    assert current_project["project_id"] == str(project.id)
    assert current_project["potentially_affected"] is True
    assert all("Chemicals" not in str(item) for item in current_project["matched_approvals"])
    assert result["impact"]["project_count"] == 2


async def test_sector_mismatch_does_not_mark_project_as_affected(db_session):
    _, project, _ = await _make_project_and_approval(db_session, department="boiler", sector="Textile")
    old = await _make_doc(db_session, department="boiler", sector="Chemicals", version="v1", text="Old")
    new = await _make_doc(
        db_session,
        department="boiler",
        sector="Chemicals",
        version="v2",
        supersedes_document_id=old.id,
        text="New",
    )

    result = await RegulatoryChangeService(db_session).diff(new.id, project_id=project.id)
    assert result["impact"]["current_project"]["potentially_affected"] is False
