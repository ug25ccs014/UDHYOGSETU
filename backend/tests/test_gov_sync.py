"""Tests for government status synchronization (spec §19) and AI query
resolution (spec §20)."""

import uuid
from datetime import datetime

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import Approval, ApplicationQuery, GovernmentApplication, Project
from app.services.gov_sync_service import GovSyncService
from app.services.query_resolution import QueryResolutionService

USER_UUID = uuid.UUID("22222222-2222-2222-2222-222222222222")


async def _make_project_and_approval(db):
    project = Project(
        user_id=USER_UUID,
        name="Sync Test",
        company_name="Sync Co",
        industry="Textile",
        sector="Textile",
        investment_amount=1000000,
        employees=20,
        location_state="Maharashtra",
    )
    db.add(project)
    await db.flush()
    approval = Approval(
        project_id=project.id,
        name="MPCB Consent to Establish",
        department="MPCB",
        status="SUBMITTED",
        submitted_at=datetime.utcnow(),
    )
    db.add(approval)
    await db.commit()
    return project, approval


async def test_track_government_application():
    async with AsyncSessionLocal() as db:
        _project, approval = await _make_project_and_approval(db)
        record = await GovSyncService(db).track(approval, "mpcb", "MPCB-123456")
        assert record.system == "mpcb"
        assert record.government_application_id == "MPCB-123456"
        # idempotent: tracking again updates the same row
        await GovSyncService(db).track(approval, "mpcb", "MPCB-999999")
        result = await db.execute(
            select(GovernmentApplication).where(GovernmentApplication.approval_id == approval.id)
        )
        rows = result.scalars().all()
        assert len(rows) == 1
        assert rows[0].government_application_id == "MPCB-999999"


async def test_sync_one_updates_approval_status():
    async with AsyncSessionLocal() as db:
        _project, approval = await _make_project_and_approval(db)
        record = await GovSyncService(db).track(approval, "mpcb", "MPCB-777777")
        result = await db.execute(
            select(GovernmentApplication).where(GovernmentApplication.approval_id == approval.id)
        )
        record = result.scalar_one()
        outcome = await GovSyncService(db).sync_one(record)
        assert outcome["current_status"] in {"SUBMITTED", "UNDER_REVIEW", "QUERY_RAISED", "APPROVED", "REJECTED"}


async def test_query_resolution_returns_explanation():
    async with AsyncSessionLocal() as db:
        _project, approval = await _make_project_and_approval(db)
        record = await GovSyncService(db).track(approval, "mpcb", "MPCB-555000")
        record.raw_response = {"data": {"query": "Please provide ETP capacity details and water meter reading."}}
        await db.commit()
        result = await QueryResolutionService(db).resolve_for_approval(approval)
        assert result["query_present"] is True
        assert result["query"]
        assert result["explanation"]
        assert result["relevant_documents"] is not None
        rows = (await db.execute(select(ApplicationQuery).where(ApplicationQuery.approval_id == approval.id))).scalars().all()
        assert len(rows) == 1
