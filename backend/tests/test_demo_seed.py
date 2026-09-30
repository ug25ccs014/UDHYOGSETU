"""Tests for the demo data seeder (spec §43)."""

import os
import sys

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)

import pytest

from app.core.database import AsyncSessionLocal
from app.models import (
    Approval,
    ApprovalRule,
    BusinessProfile,
    Document,
    Project,
    User,
    UserRole,
    business_profile_documents,
    ApplicationPreparation,
    InspectionVisit,
    InspectionVisitStatus,
    Grievance,
    inspection_visit_approvals,
)


@pytest.fixture
async def seed_rules(db_session):
    rules = [
        ApprovalRule(
            name="MPCB Consent to Establish (CTE)",
            department="MPCB",
            sector="Textile",
            conditions={
                "type": "OR",
                "conditions": [
                    {"type": "COMPARISON", "field": "has_boiler", "operator": "equals", "value": True},
                    {"type": "COMPARISON", "field": "hazardous_materials", "operator": "equals", "value": True},
                ],
            },
            is_mandatory=True,
            required_documents=["CTE application", "Site plan"],
            dependencies=[],
            estimated_processing_days=30,
            renewal_period_days=365,
            risk_level="HIGH",
            source="MPCB",
        ),
        ApprovalRule(
            name="Factory License (DISH)",
            department="DISH",
            sector="Textile",
            conditions={"type": "COMPARISON", "field": "employees", "operator": "greater_than", "value": 10},
            is_mandatory=True,
            required_documents=["Factory registration", "PID"],
            dependencies=["MPCB Consent to Establish (CTE)"],
            estimated_processing_days=15,
            renewal_period_days=365,
            risk_level="MEDIUM",
            source="DISH",
        ),
    ]
    db_session.add_all(rules)
    await db_session.commit()
    yield


async def test_seed_demo_creates_user_project_approvals_docs(seed_rules):
    import scripts.seed_demo as seeder

    report = await seeder.seed()

    assert report["email"] == "demo@abctextiles.in"
    assert report["project_id"]
    assert report["demo_submission_errors"] == []

    async with AsyncSessionLocal() as db:
        from uuid import UUID as _UUID

        from sqlalchemy import select
        user = (await db.execute(select(User).where(User.email == "demo@abctextiles.in"))).scalar_one()
        assert user.role == UserRole.ENTREPRENEUR

        project = (await db.execute(select(Project).where(Project.id == _UUID(report["project_id"])))).scalar_one()
        assert project.company_name == "ABC Textiles Pvt Ltd"

        profile = (await db.execute(
            select(BusinessProfile).where(BusinessProfile.user_id == user.id)
        )).scalar_one()
        assert profile.company_name == "ABC Textiles Pvt Ltd"
        assert profile.pan == "ABCTA1234F"
        assert profile.gstin == "27ABCTA1234F1Z5"

        approvals = (await db.execute(select(Approval).where(Approval.project_id == project.id))).scalars().all()
        assert len(approvals) >= 2
        submitted_ids = [a.application_id for a in approvals if a.status != "NOT_STARTED"]
        assert submitted_ids and all(value for value in submitted_ids)

        docs = (await db.execute(select(Document).where(Document.project_id == project.id))).scalars().all()
        assert len(docs) == 2

        vault_links = (await db.execute(
            select(business_profile_documents.c.document_id).where(
                business_profile_documents.c.business_profile_id == profile.id
            )
        )).all()
        assert len(vault_links) == 2

        visits = (await db.execute(select(InspectionVisit).where(InspectionVisit.project_id == project.id))).scalars().all()
        assert len(visits) == 1
        assert visits[0].status == InspectionVisitStatus.SCHEDULED.value
        linked_approvals = (await db.execute(
            select(inspection_visit_approvals.c.approval_id).where(
                inspection_visit_approvals.c.inspection_visit_id == visits[0].id
            )
        )).all()
        assert len(linked_approvals) == 1

        grievances = (await db.execute(
            select(Grievance).where(
                Grievance.user_id == user.id,
                Grievance.project_id == project.id,
            )
        )).scalars().all()
        assert len(grievances) == 1
        assert grievances[0].status == "OPEN"


async def test_seed_demo_is_idempotent(seed_rules):
    import scripts.seed_demo as seeder

    first = await seeder.seed()
    second = await seeder.seed()

    assert second["user_created"] is False
    assert second["project_created"] is False
    assert second["project_id"] == first["project_id"]

    async with AsyncSessionLocal() as db:
        from uuid import UUID as _UUID

        from sqlalchemy import select
        users = (await db.execute(select(User).where(User.email == "demo@abctextiles.in"))).scalars().all()
        assert len(users) == 1

        projects = (await db.execute(select(Project).where(Project.id == _UUID(first["project_id"])))).scalars().all()
        assert len(projects) == 1

        approvals = (await db.execute(select(Approval).where(Approval.project_id == _UUID(first["project_id"])))).scalars().all()
        assert len(approvals) == first["approvals_determined"]
        visits = (await db.execute(select(InspectionVisit).where(InspectionVisit.project_id == _UUID(first["project_id"])))) .scalars().all()
        assert len(visits) == 1
        assert second["demo_inspection_created"] is False
