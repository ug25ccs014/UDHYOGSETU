"""Regression tests for the Step 6 Query & Response Center."""

import uuid
from datetime import datetime

import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models import (
    Approval,
    ApplicationQuery,
    ApplicationQueryStatus,
    Document,
    GovernmentApplication,
    Project,
    User,
    UserRole,
)
from app.services.query_resolution import QueryResolutionService


async def _make_owner(db):
    user = User(
        id=uuid.uuid4(),
        email=f"q-{uuid.uuid4().hex[:10]}@example.com",
        name="Query Owner",
        phone="9876543210",
        password_hash=hash_password("Password@123"),
        role=UserRole.ENTREPRENEUR,
    )
    db.add(user)
    await db.flush()
    project = Project(
        user_id=user.id,
        name="Query Project",
        company_name="Query Co",
        industry="Textile",
        sector="Textile",
        investment_amount=1000000,
        employees=20,
        location_state="Maharashtra",
        location_district="Pune",
        location_city="Pune",
    )
    db.add(project)
    await db.flush()
    approval = Approval(
        project_id=project.id,
        name="MPCB Consent to Establish",
        department="MPCB",
        status="QUERY_RAISED",
        submitted_at=datetime.utcnow(),
    )
    db.add(approval)
    await db.flush()
    gov = GovernmentApplication(
        approval_id=approval.id,
        project_id=project.id,
        system="mpcb",
        government_application_id="MPCB-123456",
        last_synced_status="QUERY_RAISED",
        raw_response={"data": {"query": "Please provide ETP capacity details and water meter reading."}},
    )
    db.add(gov)
    await db.commit()
    return user, project, approval, gov


@pytest.mark.asyncio
async def test_query_center_persists_current_query_and_required_evidence():
    async with AsyncSessionLocal() as db:
        _user, project, approval, _gov = await _make_owner(db)
        db.add(
            Document(
                project_id=project.id,
                file_name="etp_capacity_certificate.pdf",
                file_path="test/etp_capacity_certificate.pdf",
                file_type="application/pdf",
                status="VERIFIED",
                extracted_fields={"document_type": "MPCB CONSENT", "name": "Query Co"},
                custom_metadata={"document_type": "ETP CAPACITY CERTIFICATE"},
            )
        )
        await db.commit()

        result = await QueryResolutionService(db).resolve_for_approval(approval)
        assert result["query_present"] is True
        assert result["query_id"]
        assert result["status"] == ApplicationQueryStatus.OPEN.value
        labels = {item["label"]: item["satisfied"] for item in result["required_evidence"]}
        assert labels["ETP capacity details"] is True
        assert labels["Water meter reading"] is False

        stored = (await db.execute(select(ApplicationQuery).where(ApplicationQuery.approval_id == approval.id))).scalar_one()
        assert stored.query_fingerprint


@pytest.mark.asyncio
async def test_query_response_draft_and_submission_are_persisted_without_gateway_call():
    async with AsyncSessionLocal() as db:
        _user, _project, approval, _gov = await _make_owner(db)
        center = await QueryResolutionService(db).resolve_for_approval(approval)
        query_id = center["query_id"]

        draft = await QueryResolutionService(db).save_response(
            approval, query_id, "Please find the requested supporting information attached.", True
        )
        assert draft.status == ApplicationQueryStatus.READY.value

        submitted = await QueryResolutionService(db).submit_response(approval, query_id)
        assert submitted["external_submission"] is False
        assert submitted["external_action"] == "RECORDED_LOCALLY"

        await db.refresh(approval)
        assert approval.status.value == "SUBMITTED"
        stored = (await db.execute(select(ApplicationQuery).where(ApplicationQuery.id == uuid.UUID(query_id)))).scalar_one()
        assert stored.status == ApplicationQueryStatus.SUBMITTED.value
        assert stored.submitted_response


@pytest.mark.asyncio
async def test_query_response_cannot_be_edited_after_submission():
    async with AsyncSessionLocal() as db:
        _user, _project, approval, _gov = await _make_owner(db)
        center = await QueryResolutionService(db).resolve_for_approval(approval)
        query_id = center["query_id"]
        await QueryResolutionService(db).submit_response(approval, query_id, "Response recorded")

        with pytest.raises(ValueError, match="already been submitted"):
            await QueryResolutionService(db).save_response(approval, query_id, "Change", False)

@pytest.mark.asyncio
async def test_query_center_http_get_save_and_submit_are_owner_scoped():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    async with AsyncSessionLocal() as db:
        user, _project, approval, _gov = await _make_owner(db)
        token = __import__("app.core.security", fromlist=["create_access_token"]).create_access_token(
            {"sub": str(user.id), "email": user.email, "role": "ENTREPRENEUR"}
        )

    headers = {"Authorization": f"Bearer {token}"}
    result = client.get(f"/api/applications/{approval.id}/query-center", headers=headers)
    assert result.status_code == 200, result.text
    payload = result.json()
    assert payload["query_present"] is True
    query_id = payload["query_id"]

    saved = client.patch(
        f"/api/applications/{approval.id}/query-center",
        json={"query_id": query_id, "response_text": "Please find the requested documents attached.", "ready": True},
        headers=headers,
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["status"] == "READY"

    submitted = client.post(
        f"/api/applications/{approval.id}/query-center/submit",
        json={"query_id": query_id},
        headers=headers,
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["external_submission"] is False


@pytest.mark.asyncio
async def test_query_center_cannot_access_another_users_application():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import create_access_token

    client = TestClient(app)
    async with AsyncSessionLocal() as db:
        _owner, _project, approval, _gov = await _make_owner(db)
        other = User(
            id=uuid.uuid4(),
            email=f"other-{uuid.uuid4().hex[:10]}@example.com",
            name="Other Owner",
            phone="9876543210",
            password_hash=hash_password("Password@123"),
            role=UserRole.ENTREPRENEUR,
        )
        db.add(other)
        await db.commit()
        token = create_access_token({"sub": str(other.id), "email": other.email, "role": "ENTREPRENEUR"})

    result = client.get(
        f"/api/applications/{approval.id}/query-center",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert result.status_code == 403
