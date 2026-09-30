import uuid

from app.models import (
    BusinessProfile,
    Document,
    DocumentStatus,
    IncentiveApplicationCase,
    IncentiveApplicationStatus,
    Project,
    Scheme,
    User,
)
from app.services.incentive_matcher import IncentiveMatcher
from app.services.incentive_readiness import IncentiveReadinessService


def _uid(value):
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


async def _base(db_session):
    user = User(
        email=f"incentive-{uuid.uuid4().hex[:8]}@example.com",
        name="Incentive User",
        phone="9876543210",
        password_hash="x",
    )
    db_session.add(user)
    await db_session.flush()
    project = Project(
        user_id=user.id,
        name="Textile Unit",
        company_name="Textile Industries Pvt Ltd",
        business_type="manufacturing",
        industry="Textile Manufacturing",
        sector="Textile",
        location_state="Maharashtra",
        location_district="Pune",
        location_city="Pune",
        investment_amount=20_000_000,
        employees=60,
    )
    profile = BusinessProfile(
        user_id=user.id,
        company_name=project.company_name,
        business_type=project.business_type,
        industry=project.industry,
        sector=project.sector,
        pan="ABCDE1234F",
        gstin="27ABCDE1234F1Z5",
        udyam_number="UDYAM-MH-01-1234567",
        registered_address="Pune",
        registered_state="Maharashtra",
        registered_district="Pune",
        registered_city="Pune",
    )
    scheme = Scheme(
        name="Textile Support Scheme",
        department="Directorate of Textiles",
        sector="Textile",
        location="Maharashtra",
        min_investment=10_000_000,
        max_investment=50_000_000,
        eligible_entity="Textile Processing Facility",
        employee_requirement=25,
        benefits=["40% capital subsidy"],
        application_period="Year-round",
        required_documents=["Project Report", "Land Documents", "Investment Proof"],
        source="Prototype Scheme Catalogue",
        source_url="https://example.gov/scheme",
    )
    db_session.add_all([project, profile, scheme])
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(project)
    await db_session.refresh(scheme)
    return user, project, profile, scheme


class TestIncentiveReadinessService:
    async def test_canonical_matcher_exposes_required_documents(self, db_session):
        _user, project, _profile, scheme = await _base(db_session)
        matches = await IncentiveMatcher(db_session).find_matching_schemes({
            "industry": project.industry,
            "sector": project.sector,
            "state": project.location_state,
            "investment_amount": project.investment_amount,
            "employees": project.employees,
        })
        assert matches
        match = next(item for item in matches if item["id"] == str(scheme.id))
        assert match["required_documents"] == scheme.required_documents
        assert match["source"] == scheme.source

    async def test_readiness_reports_missing_documents_and_manual_entity_review(self, db_session):
        user, project, _profile, _scheme = await _base(db_session)
        result = await IncentiveReadinessService(db_session).project_readiness(project.id, user.id)
        assert result["count"] == 1
        match = result["matches"][0]
        assert match["readiness_state"] == "ACTION_REQUIRED"
        assert match["document_summary"]["missing"] == 3
        assert match["eligibility"]["manual_confirmation_required"] is True
        assert any(item["key"] == "eligible_entity" and item["status"] == "REVIEW" for item in match["eligibility"]["criteria"])

    async def test_ready_pack_can_be_prepared_and_selected_documents_persist(self, db_session):
        user, project, _profile, scheme = await _base(db_session)
        docs = []
        for index, name in enumerate(["Project Report.pdf", "Land Documents.pdf", "Investment Proof.pdf"]):
            docs.append(Document(
                project_id=project.id,
                file_name=name,
                file_path=f"/tmp/{index}-{name}",
                file_type="application/pdf",
                file_size=100,
                status=DocumentStatus.VERIFIED,
                extracted_fields={"document_type": name[:-4]},
            ))
        db_session.add_all(docs)
        await db_session.commit()
        await db_session.refresh(docs[0])
        await db_session.refresh(docs[1])
        await db_session.refresh(docs[2])

        readiness = await IncentiveReadinessService(db_session).scheme_readiness(project.id, scheme.id, user.id)
        assert readiness["document_summary"]["ready"] == 3
        assert readiness["readiness_state"] == "REVIEW_RECOMMENDED"

        case = await IncentiveReadinessService(db_session).prepare_case(
            project.id, scheme.id, user.id, document_ids=[doc.id for doc in docs], notes="Prepared for review"
        )
        assert case["case_id"]
        assert case["status"] == IncentiveApplicationStatus.PREPARING.value
        assert len(case["document_ids"]) == 3

    async def test_external_submission_requires_ready_case(self, db_session):
        user, project, _profile, scheme = await _base(db_session)
        service = IncentiveReadinessService(db_session)
        case = await service.prepare_case(project.id, scheme.id, user.id)
        try:
            await service.update_case(
                uuid.UUID(case["case_id"]),
                user.id,
                status=IncentiveApplicationStatus.SUBMITTED_EXTERNALLY.value,
            )
            assert False, "Expected submission guard"
        except ValueError as exc:
            assert "ready for submission" in str(exc).lower()

    async def test_ready_status_cannot_bypass_readiness_blockers(self, db_session):
        user, project, _profile, scheme = await _base(db_session)
        scheme.eligible_entity = None
        await db_session.commit()
        service = IncentiveReadinessService(db_session)
        case = await service.prepare_case(project.id, scheme.id, user.id)
        try:
            await service.update_case(
                uuid.UUID(case["case_id"]),
                user.id,
                status=IncentiveApplicationStatus.READY_FOR_SUBMISSION.value,
            )
            assert False, "Expected readiness guard"
        except ValueError as exc:
            assert "not ready for submission" in str(exc).lower()

    async def test_other_users_cannot_access_or_update_case(self, db_session):
        owner, project, _profile, scheme = await _base(db_session)
        case = await IncentiveReadinessService(db_session).prepare_case(project.id, scheme.id, owner.id)
        other = User(
            email=f"other-{uuid.uuid4().hex[:8]}@example.com",
            name="Other",
            phone="9876543211",
            password_hash="x",
        )
        db_session.add(other)
        await db_session.commit()
        try:
            await IncentiveReadinessService(db_session).case_detail(uuid.UUID(case["case_id"]), other.id)
            assert False, "Expected ownership failure"
        except ValueError as exc:
            assert "not found" in str(exc).lower()


class TestIncentiveReadinessRouteContract:
    def test_routes_registered(self):
        from app.main import app

        paths = {route.path for route in app.routes if hasattr(route, "path")}
        assert "/api/schemes/projects/{project_id}/readiness" in paths
        assert "/api/schemes/projects/{project_id}/{scheme_id}/readiness" in paths
        assert "/api/schemes/projects/{project_id}/{scheme_id}/prepare" in paths
        assert "/api/schemes/incentive-cases/{case_id}" in paths

    def test_migration_revision_is_0014(self):
        from pathlib import Path

        migration = Path("alembic/versions/0014_incentive_application_readiness.py")
        text = migration.read_text()
        assert 'revision = "0014"' in text
        assert 'down_revision = "0013"' in text
