"""Tests for the Explore Government Services module.

Covers the catalog APIs, deterministic applicability, the checklist flow
(NOT_STARTED -> DRAFT -> SUBMITTED with document attachment), ownership/role
security, and the officer review surface. Uses the same TestClient + SQLite
setup as ``test_api.py`` and inserts fixture data directly into the session.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import hash_password
from app.main import app
from app.models import ApprovalRule, GovernmentService, User, UserRole

client = TestClient(app)

_PASSWORD = "Password@123"


def _unique_email(prefix="ent"):
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


def _register(email=None):
    payload = {
        "email": email or _unique_email(),
        "name": "Test User",
        "phone": "9876543210",
        "password": _PASSWORD,
        "role": "ENTREPRENEUR",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _auth_headers(email=None):
    email = email or _unique_email()
    _register(email=email)
    response = client.post("/api/auth/login", json={"email": email, "password": _PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _privileged_token(db_session, role):
    """Create an OFFICER/ADMIN user directly (self-registration of privileged
    roles is blocked), keeping the salted hash so login works."""
    email = _unique_email(role.lower())
    user = User(
        email=email,
        name=f"{role.title()} One",
        phone="9876543211",
        password_hash=hash_password(_PASSWORD),
        role=UserRole[role.upper()],
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    response = client.post("/api/auth/login", json={"email": email, "password": _PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _project_payload():
    return {
        "company_name": "Explore Test Pvt Ltd",
        "business_type": "manufacturing",
        "industry": "Textiles",
        "sector": "Textile",
        "project_name": "Explore Garment Factory",
        "is_new": True,
        "project_stage": "implementation",
        "investment_amount": 5000000.0,
        "location_state": "Maharashtra",
        "location_district": "Pune",
        "location_city": "Pimpri-Chinchwad",
        "location_industrial_area": "MIDC Bhosari",
        "location_midc_estate": "MIDC Bhosari",
        "land_type": "leased",
        "employees": 120,
        "production_type": "continuous",
        "hazardous_materials": False,
        "has_boiler": True,
        "electricity_load": 350.0,
        "water_consumption": 2000.0,
        "pollution_potential": "high",
        "building_type": "industrial",
    }


def _create_project(headers=None):
    headers = headers or _auth_headers()
    response = client.post("/api/projects", json=_project_payload(), headers=headers)
    assert response.status_code == 200, response.text
    return response.json()




def _attach_fire_required_documents(project_id: str, approval_id: str, headers: dict) -> None:
    """Create validated text fixtures for all Fire NOC required documents."""
    fixtures = [
        ("building_layout.txt", "Explore Test Pvt Ltd\nBuilding Layout"),
        ("fire_safety_plan.txt", "Explore Test Pvt Ltd\nFire Safety Plan"),
        ("noc_undertaking.txt", "Explore Test Pvt Ltd\nNoC Undertaking"),
    ]
    for filename, content in fixtures:
        upload = client.post(
            "/api/documents/upload",
            params={"project_id": project_id},
            files={"file": (filename, content.encode(), "text/plain")},
            headers=headers,
        )
        assert upload.status_code == 200, upload.text
        document = upload.json()
        assert document["status"] == "VERIFIED", document
        attach = client.post(
            f"/api/explore/checklist/{approval_id}/attach-document",
            json={"document_id": document["id"]},
            headers=headers,
        )
        assert attach.status_code == 200, attach.text


FIRE_RULE_CONDITIONS = {
    "type": "OR",
    "conditions": [
        {"type": "COMPARISON", "field": "employees", "operator": "greater_than", "value": 9},
        {"type": "COMPARISON", "field": "hazardous_materials", "operator": "equals", "value": True},
    ],
}


async def _seed_catalog(db_session, rule_name="Fire No Objection Certificate"):
    """Insert an ApprovalRule + a linked GovernmentService + an unlinked one."""
    result = await db_session.execute(select(ApprovalRule).where(ApprovalRule.name == rule_name))
    rule = result.scalar_one_or_none()
    if not rule:
        rule = ApprovalRule(
            name=rule_name,
            department="Fire Services Department",
            sector="All",
            conditions=FIRE_RULE_CONDITIONS,
            is_mandatory=True,
            required_documents=["Building Layout", "Fire Safety Plan", "NoC Undertaking"],
            dependencies=[],
            estimated_processing_days=20,
            renewal_period_days=365,
            risk_level="MEDIUM",
        )
        db_session.add(rule)
        await db_session.flush()

    result = await db_session.execute(
        select(GovernmentService).where(GovernmentService.slug == "fire-noc")
    )
    if not result.scalar_one_or_none():
        db_session.add(
            GovernmentService(
                slug="fire-noc",
                name="Fire No Objection Certificate",
                description="Fire safety NOC",
                category="Safety & Health",
                authority="Maharashtra Fire Services",
                department="Fire Services Department",
                service_type="NOC",
                application_mode="INTEGRATED",
                official_reference="Fire Act",
                applicable_documents=[
                    {"document_type": "Building Layout", "description": "Plan", "required": True},
                    {"document_type": "NoC Undertaking", "description": "Signed", "required": True},
                ],
                risk_level="MEDIUM",
                sla_days=20,
                renewal_period_days=365,
                approval_rule_id=rule.id,
                gateway_system="fire",
                is_demo=True,
            )
        )
    result = await db_session.execute(
        select(GovernmentService).where(GovernmentService.slug == "udyam-registration")
    )
    if not result.scalar_one_or_none():
        db_session.add(
            GovernmentService(
                slug="udyam-registration",
                name="Udyam MSME Registration",
                description="MSME self-registration",
                category="Tax & Registration",
                authority="DIC",
                department="District Industries Centre",
                service_type="REGISTRATION",
                application_mode="REDIRECT",
                external_portal_url="https://udyamregistration.gov.in",
                applicable_documents=[
                    {"document_type": "PAN Card", "description": "PAN", "required": True}
                ],
                risk_level="LOW",
                sla_days=2,
                approval_rule_id=None,
                is_demo=False,
            )
        )
    await db_session.commit()


@pytest.fixture
async def catalog(db_session):
    await _seed_catalog(db_session)
    return db_session


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------
class TestCatalog:
    def test_list_services_requires_auth(self):
        response = client.get("/api/explore/services")
        assert response.status_code == 401

    async def test_list_services(self, catalog):
        headers = _auth_headers()
        response = client.get("/api/explore/services", headers=headers)
        assert response.status_code == 200
        slugs = [s["slug"] for s in response.json()]
        assert "fire-noc" in slugs
        assert "udyam-registration" in slugs

    async def test_search_by_name(self, catalog):
        headers = _auth_headers()
        response = client.get("/api/explore/services?q=udyam", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["slug"] == "udyam-registration"

    async def test_filter_by_category(self, catalog):
        headers = _auth_headers()
        response = client.get(
            "/api/explore/services",
            params={"category": "Safety & Health"},
            headers=headers,
        )
        assert response.status_code == 200
        slugs = [s["slug"] for s in response.json()]
        assert slugs == ["fire-noc"]

    async def test_filter_by_mode(self, catalog):
        headers = _auth_headers()
        response = client.get("/api/explore/services?application_mode=REDIRECT", headers=headers)
        slugs = [s["slug"] for s in response.json()]
        assert slugs == ["udyam-registration"]

    async def test_categories(self, catalog):
        headers = _auth_headers()
        response = client.get("/api/explore/services/categories", headers=headers)
        assert response.status_code == 200
        categories = response.json()["categories"]
        assert "Safety & Health" in categories
        assert "Tax & Registration" in categories

    async def test_get_service_by_slug(self, catalog):
        headers = _auth_headers()
        response = client.get("/api/explore/services/fire-noc", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Fire No Objection Certificate"
        assert body["application_mode"] == "INTEGRATED"
        assert body["is_demo"] is True
        assert body["service_type"] == "NOC"
        assert body["integration"]["classification"] == "PROTOTYPE_SIMULATOR"
        assert body["integration"]["is_simulated"] is True

    async def test_get_service_by_uuid(self, catalog, db_session):
        result = await db_session.execute(
            select(GovernmentService).where(GovernmentService.slug == "fire-noc")
        )
        service = result.scalar_one_or_none()
        headers = _auth_headers()
        response = client.get(f"/api/explore/services/{service.id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["slug"] == "fire-noc"

    async def test_get_unknown_service_404(self, catalog):
        headers = _auth_headers()
        response = client.get("/api/explore/services/not-a-service", headers=headers)
        assert response.status_code == 404

    async def test_service_documents(self, catalog):
        headers = _auth_headers()
        project = _create_project(headers=headers)
        response = client.get(
            f"/api/explore/services/fire-noc/documents?project_id={project['id']}",
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        types = {d["document_type"] for d in body["required_documents"]}
        assert "Building Layout" in types
        assert "NoC Undertaking" in types
        # rule-level required doc is merged in
        assert "Fire Safety Plan" in types


# ---------------------------------------------------------------------------
# Applicability
# ---------------------------------------------------------------------------
class TestApplicability:
    def _check(self, project_id, slug="fire-noc", headers=None):
        headers = headers or _auth_headers()
        return client.post(
            f"/api/explore/services/{slug}/check-applicability",
            json={"project_id": project_id},
            headers=headers,
        )

    async def test_applicable(self, catalog):
        headers = _auth_headers()
        project = _create_project(headers=headers)  # 120 employees > 9
        response = self._check(project["id"], headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "APPLICABLE"
        assert body["matched_conditions"]
        assert body["failed_conditions"] == []
        assert "Building Layout" in body["required_documents"]

    async def test_not_applicable(self, catalog):
        headers = _auth_headers()
        payload = {
            **_project_payload(),
            "business_type": "trading",
            "project_stage": "operation",
            "employees": 3,
            "pollution_potential": "low",
            "has_boiler": False,
            "hazardous_materials": False,
            "project_name": "Trading Outlet",
        }
        response = client.post("/api/projects", json=payload, headers=headers)
        assert response.status_code == 200, response.text
        project_id = response.json()["id"]
        body = self._check(project_id, headers=headers).json()
        assert body["status"] == "NOT_APPLICABLE"
        assert body["failed_conditions"]

    async def test_not_determined_for_unlinked_service(self, catalog):
        headers = _auth_headers()
        project = _create_project(headers=headers)
        body = self._check(project["id"], slug="udyam-registration", headers=headers).json()
        assert body["status"] == "NOT_DETERMINED"
        assert "no deterministic applicability rule" in body["reason"].lower()

    async def test_applicability_requires_owner(self, catalog):
        owner_headers = _auth_headers()
        project = _create_project(headers=owner_headers)
        intruder_headers = _auth_headers()
        response = self._check(project["id"], headers=intruder_headers)
        assert response.status_code == 403

    async def test_applicability_missing_project_404(self, catalog):
        headers = _auth_headers()
        response = self._check(str(uuid.uuid4()), headers=headers)
        assert response.status_code == 404

    def test_applicability_requires_auth(self):
        response = client.post(
            "/api/explore/services/fire-noc/check-applicability",
            json={"project_id": str(uuid.uuid4())},
        )
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Checklist / application lifecycle
# ---------------------------------------------------------------------------
class TestChecklist:
    async def test_add_to_checklist_creates_not_started(self, catalog):
        headers = _auth_headers()
        project = _create_project(headers=headers)
        response = client.post(
            "/api/explore/services/fire-noc/checklist",
            json={"project_id": project["id"]},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "NOT_STARTED"
        assert body["created"] is True
        assert body["name"] == "Fire No Objection Certificate"
        approval_id = body["approval_id"]

        response2 = client.post(
            "/api/explore/services/fire-noc/checklist",
            json={"project_id": project["id"]},
            headers=headers,
        )
        assert response2.json()["created"] is False
        assert response2.json()["approval_id"] == approval_id

    async def test_add_to_checklist_requires_owner(self, catalog):
        owner_headers = _auth_headers()
        project = _create_project(headers=owner_headers)
        intruder_headers = _auth_headers()
        response = client.post(
            "/api/explore/services/fire-noc/checklist",
            json={"project_id": project["id"]},
            headers=intruder_headers,
        )
        assert response.status_code == 403

    async def test_start_transitions_to_draft(self, catalog):
        headers = _auth_headers()
        project = _create_project(headers=headers)
        checklist = client.post(
            "/api/explore/services/fire-noc/checklist",
            json={"project_id": project["id"]},
            headers=headers,
        ).json()
        approval_id = checklist["approval_id"]
        response = client.post(f"/api/explore/checklist/{approval_id}/start", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "DRAFT"

    async def test_attach_and_detach_document(self, catalog):
        headers = _auth_headers()
        project = _create_project(headers=headers)
        checklist = client.post(
            "/api/explore/services/fire-noc/checklist",
            json={"project_id": project["id"]},
            headers=headers,
        ).json()
        approval_id = checklist["approval_id"]

        upload = client.post(
            "/api/documents/upload",
            params={"project_id": project["id"]},
            files={"file": ("layout.pdf", b"Building layout", "application/pdf")},
            headers=headers,
        )
        assert upload.status_code == 200, upload.text
        document_id = upload.json()["id"]

        attach = client.post(
            f"/api/explore/checklist/{approval_id}/attach-document",
            json={"document_id": document_id},
            headers=headers,
        )
        assert attach.status_code == 200
        assert attach.json()["attached"] is True

        detail = client.get(f"/api/explore/checklist/{approval_id}", headers=headers).json()
        assert any(d["id"] == document_id for d in detail["attached_documents"])

        detach = client.post(
            f"/api/explore/checklist/{approval_id}/detach-document",
            json={"document_id": document_id},
            headers=headers,
        )
        assert detach.status_code == 200
        assert detach.json()["attached"] is False

    async def test_attach_other_users_document_403(self, catalog):
        owner_headers = _auth_headers()
        project = _create_project(headers=owner_headers)
        approval_id = client.post(
            "/api/explore/services/fire-noc/checklist",
            json={"project_id": project["id"]},
            headers=owner_headers,
        ).json()["approval_id"]

        intruder_headers = _auth_headers()
        intruder_project = _create_project(headers=intruder_headers)
        upload = client.post(
            "/api/documents/upload",
            params={"project_id": intruder_project["id"]},
            files={"file": ("doc.pdf", b"data", "application/pdf")},
            headers=intruder_headers,
        )
        foreign_document = upload.json()["id"]
        response = client.post(
            f"/api/explore/checklist/{approval_id}/attach-document",
            json={"document_id": foreign_document},
            headers=intruder_headers,
        )
        assert response.status_code == 403

    async def test_other_users_checklist_403(self, catalog):
        owner_headers = _auth_headers()
        project = _create_project(headers=owner_headers)
        approval_id = client.post(
            "/api/explore/services/fire-noc/checklist",
            json={"project_id": project["id"]},
            headers=owner_headers,
        ).json()["approval_id"]

        intruder_headers = _auth_headers()
        response = client.get(f"/api/explore/checklist/{approval_id}", headers=intruder_headers)
        assert response.status_code == 403

    async def test_full_flow_submit(self, catalog):
        """checklist -> start -> attach -> submit via existing application API."""
        headers = _auth_headers()
        project = _create_project(headers=headers)
        approval_id = client.post(
            "/api/explore/services/fire-noc/checklist",
            json={"project_id": project["id"]},
            headers=headers,
        ).json()["approval_id"]

        client.post(f"/api/explore/checklist/{approval_id}/start", headers=headers)

        _attach_fire_required_documents(project["id"], approval_id, headers)

        submit = client.post(f"/api/applications/{approval_id}/submit", headers=headers)
        assert submit.status_code == 200, submit.text
        assert submit.json()["status"] == "SUBMITTED"

        listing = client.get("/api/applications", headers=headers).json()
        assert any(a["approval_name"] == "Fire No Objection Certificate" for a in listing["applications"])


# ---------------------------------------------------------------------------
# Officer review surface
# ---------------------------------------------------------------------------
class TestOfficerReview:
    def test_officer_endpoints_require_officer(self):
        entrepreneur = _auth_headers()
        response = client.get("/api/officer/applications", headers=entrepreneur)
        assert response.status_code == 403

    async def test_officer_list_and_transition(self, catalog, db_session):
        officer = await _privileged_token(db_session, "OFFICER")
        headers = _auth_headers()
        project = _create_project(headers=headers)
        approval_id = client.post(
            "/api/explore/services/fire-noc/checklist",
            json={"project_id": project["id"]},
            headers=headers,
        ).json()["approval_id"]
        client.post(f"/api/explore/checklist/{approval_id}/start", headers=headers)
        _attach_fire_required_documents(project["id"], approval_id, headers)
        assert client.post(f"/api/applications/{approval_id}/submit", headers=headers).status_code == 200

        listing = client.get("/api/officer/applications?status=SUBMITTED", headers=officer)
        assert listing.status_code == 200
        apps = listing.json()["applications"]
        assert any(a["approval_id"] == approval_id for a in apps)

        detail = client.get(f"/api/officer/applications/{approval_id}", headers=officer)
        assert detail.status_code == 200
        body = detail.json()
        assert body["owner_email"]
        assert "UNDER_REVIEW" in {t["to"] for t in body["available_transitions"]}

        transition = client.post(
            f"/api/officer/applications/{approval_id}/transition",
            json={"to_status": "UNDER_REVIEW"},
            headers=officer,
        )
        assert transition.status_code == 200, transition.text
        assert transition.json()["status"] == "UNDER_REVIEW"

        approve = client.post(
            f"/api/officer/applications/{approval_id}/transition",
            json={"to_status": "APPROVED"},
            headers=officer,
        )
        assert approve.status_code == 200, approve.text
        assert approve.json()["status"] == "APPROVED"

    async def test_officer_invalid_transition_400(self, catalog, db_session):
        officer = await _privileged_token(db_session, "OFFICER")
        headers = _auth_headers()
        project = _create_project(headers=headers)
        approval_id = client.post(
            "/api/explore/services/fire-noc/checklist",
            json={"project_id": project["id"]},
            headers=headers,
        ).json()["approval_id"]
        response = client.post(
            f"/api/officer/applications/{approval_id}/transition",
            json={"to_status": "INSPECTION"},
            headers=officer,
        )
        assert response.status_code == 400

    async def test_officer_sync_tracks_application(self, catalog, db_session):
        officer = await _privileged_token(db_session, "OFFICER")
        headers = _auth_headers()
        project = _create_project(headers=headers)
        approval_id = client.post(
            "/api/explore/services/fire-noc/checklist",
            json={"project_id": project["id"]},
            headers=headers,
        ).json()["approval_id"]
        client.post(f"/api/explore/checklist/{approval_id}/start", headers=headers)
        _attach_fire_required_documents(project["id"], approval_id, headers)
        assert client.post(f"/api/applications/{approval_id}/submit", headers=headers).status_code == 200

        sync = client.post(f"/api/officer/applications/{approval_id}/sync", headers=officer)
        assert sync.status_code == 200, sync.text
        body = sync.json()
        assert body["synced"] >= 1, body
        assert body["items"], body
        assert body["items"][0]["government_application_id"]
        assert body["items"][0]["system"] == "fire"
        assert body["items"][0]["current_status"] in (
            "SUBMITTED", "UNDER_REVIEW", "INSPECTION", "QUERY_RAISED", "APPROVED", "REJECTED",
        )

        detail = client.get(f"/api/officer/applications/{approval_id}", headers=officer).json()
        assert detail["government"]["system"] == "fire"
        assert detail["government"]["government_application_id"]

    def test_officer_review_requires_auth(self):
        assert client.get("/api/officer/applications/does-not-exist").status_code == 401


# ---------------------------------------------------------------------------
# Admin catalog management
# ---------------------------------------------------------------------------
class TestAdminCatalog:
    def test_admin_required(self):
        entrepreneur = _auth_headers()
        response = client.post(
            "/api/explore/admin/services",
            json={},
            headers=entrepreneur,
        )
        assert response.status_code == 403

    async def test_admin_create_and_update(self, catalog, db_session):
        admin = await _privileged_token(db_session, "ADMIN")

        created = client.post(
            "/api/explore/admin/services",
            json={
                "slug": "new-service",
                "name": "New Test Service",
                "category": "Test",
                "authority": "Test Authority",
                "department": "Test Dept",
                "service_type": "APPROVAL",
                "application_mode": "GUIDED",
            },
            headers=admin,
        )
        assert created.status_code == 201, created.text

        updated = client.patch(
            "/api/explore/admin/services/new-service",
            json={"name": "Renamed Service", "sla_days": 14},
            headers=admin,
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "Renamed Service"
        assert updated.json()["sla_days"] == 14

        dup = client.post(
            "/api/explore/admin/services",
            json={
                "slug": "new-service",
                "name": "Another",
                "category": "Test",
                "authority": "Test Authority",
                "department": "Test Dept",
            },
            headers=admin,
        )
        assert dup.status_code == 409

    async def test_validate_reserved_service_fields_ignored(self, catalog, db_session):
        """PATCH must not let a non-admin request change slug/approval_rule_id."""
        admin = await _privileged_token(db_session, "ADMIN")
        response = client.patch(
            "/api/explore/admin/services/fire-noc",
            json={"slug": "hijacked", "approval_rule_id": "00000000-0000-0000-0000-000000000000"},
            headers=admin,
        )
        assert response.status_code == 200
        assert response.json()["slug"] == "fire-noc"