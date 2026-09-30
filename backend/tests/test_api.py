"""End-to-end API tests for UDYOGSETU.

These exercise the real FastAPI application over HTTP via TestClient against
the throwaway SQLite database wired up in ``conftest.py``.
"""

import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _unique_email(prefix="user"):
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


_PASSWORD = "Password@123"


def _register(email=None, password=_PASSWORD):
    payload = {
        "email": email or _unique_email(),
        "name": "Test User",
        "phone": "9876543210",
        "password": password,
        "role": "ENTREPRENEUR",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _project_payload():
    return {
        "company_name": "Test Industries Pvt Ltd",
        "business_type": "manufacturing",
        "industry": "Textiles",
        "sector": "Textile",
        "project_name": "Test Garment Factory",
        "is_new": True,
        "project_stage": "feasibility",
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
        "pollution_potential": "medium",
        "building_type": "industrial",
    }


def _auth_headers(email=None):
    email = email or _unique_email()
    _register(email=email)
    response = client.post("/api/auth/login", json={"email": email, "password": _PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_project(headers=None):
    headers = headers or _auth_headers()
    response = client.post("/api/projects", json=_project_payload(), headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


class TestHealthEndpoint:
    def test_health(self):
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert "version" in body
        assert "X-Request-ID" in response.headers


class TestAuthEndpoints:
    def test_register_success(self):
        user = _register()
        assert user["email"].startswith("user-")
        assert user["name"] == "Test User"
        assert user["role"] == "ENTREPRENEUR"
        assert user["is_active"] is True
        assert "id" in user
        assert "created_at" in user

    def test_register_duplicate_email_conflict(self):
        email = _unique_email()
        _register(email=email)
        response = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "name": "Test User",
                "phone": "9876543210",
                "password": _PASSWORD,
                "role": "ENTREPRENEUR",
            },
        )
        assert response.status_code == 409

    def test_register_weak_password_422(self):
        response = client.post(
            "/api/auth/register",
            json={
                "email": _unique_email(),
                "name": "Test User",
                "phone": "9876543210",
                "password": "123",
                "role": "ENTREPRENEUR",
            },
        )
        assert response.status_code == 422

    def test_register_invalid_phone_422(self):
        response = client.post(
            "/api/auth/register",
            json={
                "email": _unique_email(),
                "name": "Test User",
                "phone": "123",
                "password": _PASSWORD,
                "role": "ENTREPRENEUR",
            },
        )
        assert response.status_code == 422

    def test_register_invalid_email_422(self):
        response = client.post(
            "/api/auth/register",
            json={
                "email": "not-an-email",
                "name": "Test User",
                "phone": "9876543210",
                "password": _PASSWORD,
                "role": "ENTREPRENEUR",
            },
        )
        assert response.status_code == 422

    def test_login_success(self):
        email = _unique_email()
        _register(email=email)
        response = client.post(
            "/api/auth/login",
            json={"email": email, "password": _PASSWORD},
        )
        assert response.status_code == 200
        token = response.json()
        assert token["access_token"]
        assert token["token_type"] == "bearer"
        assert token["expires_in"] == 86400

    def test_login_wrong_password_401(self):
        email = _unique_email()
        _register(email=email)
        response = client.post(
            "/api/auth/login",
            json={"email": email, "password": "WrongPassword1"},
        )
        assert response.status_code == 401

    def test_login_unknown_user_401(self):
        response = client.post(
            "/api/auth/login",
            json={"email": _unique_email(), "password": _PASSWORD},
        )
        assert response.status_code == 401

    def test_refresh_token(self):
        headers = _auth_headers()
        response = client.post("/api/auth/refresh", headers=headers)
        assert response.status_code == 200
        token = response.json()
        assert token["access_token"]
        assert token["token_type"] == "bearer"

    def test_refresh_token_requires_auth(self):
        response = client.post("/api/auth/refresh")
        assert response.status_code == 401


class TestProjectEndpoints:
    def test_create_project_requires_auth(self):
        response = client.post("/api/projects", json=_project_payload())
        assert response.status_code == 401

    def test_create_project(self):
        project = _create_project()
        assert "id" in project
        assert project["name"] == "Test Garment Factory"
        assert project["company_name"] == "Test Industries Pvt Ltd"
        assert project["location_state"] == "Maharashtra"

    def test_get_project_by_id(self):
        headers = _auth_headers()
        project = _create_project(headers=headers)
        response = client.get(f"/api/projects/{project['id']}", headers=headers)
        assert response.status_code == 200
        assert response.json()["name"] == "Test Garment Factory"

    def test_get_project_requires_auth(self):
        headers = _auth_headers()
        project = _create_project(headers=headers)
        response = client.get(f"/api/projects/{project['id']}")
        assert response.status_code == 401

    def test_get_other_users_project_403(self):
        owner_headers = _auth_headers()
        project = _create_project(headers=owner_headers)
        intruder_headers = _auth_headers()
        response = client.get(f"/api/projects/{project['id']}", headers=intruder_headers)
        assert response.status_code == 403

    def test_list_my_projects(self):
        headers = _auth_headers()
        project = _create_project(headers=headers)
        other_headers = _auth_headers()
        _create_project(headers=other_headers)

        response = client.get("/api/projects", headers=headers)
        assert response.status_code == 200
        ids = [p["id"] for p in response.json()]
        assert project["id"] in ids
        assert len(ids) == 1

    def test_list_projects_requires_auth(self):
        response = client.get("/api/projects")
        assert response.status_code == 401

    def test_get_missing_project_404(self):
        headers = _auth_headers()
        response = client.get(f"/api/projects/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404

    def test_get_invalid_project_id_422(self):
        headers = _auth_headers()
        response = client.get("/api/projects/not-a-uuid", headers=headers)
        assert response.status_code == 422

    def test_analyze_project(self):
        headers = _auth_headers()
        project = _create_project(headers=headers)
        response = client.post(f"/api/projects/{project['id']}/analyze", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["project_id"] == project["id"]
        assert body["applicable_approvals"] == []
        assert body["total_count"] == 0
        assert body["mandatory_count"] == 0

    def test_analyze_other_users_project_403(self):
        owner_headers = _auth_headers()
        project = _create_project(headers=owner_headers)
        intruder_headers = _auth_headers()
        response = client.post(f"/api/projects/{project['id']}/analyze", headers=intruder_headers)
        assert response.status_code == 403

    def test_project_approvals_empty(self):
        headers = _auth_headers()
        project = _create_project(headers=headers)
        response = client.get(f"/api/projects/{project['id']}/approvals", headers=headers)
        assert response.status_code == 200
        assert response.json() == []


class TestDocumentEndpoints:
    def test_upload_and_fetch_document(self):
        headers = _auth_headers()
        project = _create_project(headers=headers)
        upload = client.post(
            "/api/documents/upload",
            params={"project_id": project["id"]},
            files={"file": ("factory-license.txt", b"Factory License\nCompany: Test Corp", "text/plain")},
            headers=headers,
        )
        assert upload.status_code == 200, upload.text
        document = upload.json()
        assert document["file_name"] == "factory-license.txt"
        assert document["file_type"] == "text/plain"
        assert "id" in document

        fetched = client.get(f"/api/documents/{document['id']}", headers=headers)
        assert fetched.status_code == 200
        assert fetched.json()["file_name"] == "factory-license.txt"

    def test_upload_requires_auth(self):
        response = client.post(
            "/api/documents/upload",
            params={"project_id": uuid.uuid4()},
            files={"file": ("a.txt", b"x", "text/plain")},
        )
        assert response.status_code == 401

    def test_upload_rejects_unsupported_type(self):
        headers = _auth_headers()
        project = _create_project(headers=headers)
        upload = client.post(
            "/api/documents/upload",
            params={"project_id": project["id"]},
            files={"file": ("malware.exe", b"MZ...", "application/x-msdownload")},
            headers=headers,
        )
        assert upload.status_code == 400

    def test_get_missing_document_404(self):
        headers = _auth_headers()
        response = client.get(f"/api/documents/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404

    def test_get_other_users_document_403(self):
        owner_headers = _auth_headers()
        project = _create_project(headers=owner_headers)
        upload = client.post(
            "/api/documents/upload",
            params={"project_id": project["id"]},
            files={"file": ("lic.txt", b"some content", "text/plain")},
            headers=owner_headers,
        )
        assert upload.status_code == 200, upload.text
        document = upload.json()

        intruder_headers = _auth_headers()
        response = client.get(f"/api/documents/{document['id']}", headers=intruder_headers)
        assert response.status_code == 403

    def test_validate_document(self):
        headers = _auth_headers()
        project = _create_project(headers=headers)
        upload = client.post(
            "/api/documents/upload",
            params={"project_id": project["id"]},
            files={"file": ("lic.txt", b"some content", "text/plain")},
            headers=headers,
        )
        assert upload.status_code == 200, upload.text
        document = upload.json()

        validation = client.post(f"/api/documents/{document['id']}/validate", headers=headers)
        assert validation.status_code == 200
        body = validation.json()
        assert body["document_id"] == document["id"]
        assert "status" in body
        assert "extracted_fields" in body
        assert "validation_errors" in body


class TestRegulatoryEndpoints:
    def test_query_regulatory_knowledge(self):
        headers = _auth_headers()
        project = _create_project(headers=headers)
        response = client.post(
            "/api/regulatory/query",
            json={"query": "boiler registration rules", "project_id": project["id"]},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert "answer" in body
        assert "sources" in body
        assert "evidence" in body
        assert body["confidence"] == 0.0

    def test_query_requires_auth(self):
        response = client.post(
            "/api/regulatory/query",
            json={"query": "boiler registration rules", "project_id": str(uuid.uuid4())},
        )
        assert response.status_code == 401

    def test_chat_copilot(self):
        headers = _auth_headers()
        project = _create_project(headers=headers)
        response = client.post(
            "/api/regulatory/chat",
            json={"query": "mpcb consent requirements", "project_id": project["id"]},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert "response" in body
        assert "sources" in body

    def test_rag_chat_endpoint(self):
        headers = _auth_headers()
        project = _create_project(headers=headers)
        response = client.post(
            "/api/chat/query",
            json={"question": "What is required for boiler registration?", "project_id": project["id"]},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert "answer" in body
        assert "confidence" in body

    def test_rag_chat_requires_auth(self):
        response = client.post(
            "/api/chat/query",
            json={"question": "What is required for boiler registration?"},
        )
        assert response.status_code == 401


class TestComplianceEndpoints:
    def test_compliance_dashboard_empty(self):
        headers = _auth_headers()
        project = _create_project(headers=headers)
        response = client.get(f"/api/compliance/{project['id']}", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["project_id"] == project["id"]
        assert body["overall_score"] == 0
        assert body["categories"] == {}

    def test_compliance_items_empty(self):
        headers = _auth_headers()
        project = _create_project(headers=headers)
        response = client.get(f"/api/compliance/{project['id']}/items", headers=headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_compliance_requires_auth(self):
        response = client.get(f"/api/compliance/{uuid.uuid4()}")
        assert response.status_code == 401

    def test_compliance_other_users_project_403(self):
        owner_headers = _auth_headers()
        project = _create_project(headers=owner_headers)
        intruder_headers = _auth_headers()
        response = client.get(f"/api/compliance/{project['id']}", headers=intruder_headers)
        assert response.status_code == 403

    def test_compliance_score_after_analyze(self):
        headers = _auth_headers()
        project = _create_project(headers=headers)
        response = client.post(f"/api/projects/{project['id']}/analyze", headers=headers)
        assert response.status_code == 200, response.text
        score_response = client.get(f"/api/compliance/{project['id']}/score", headers=headers)
        assert score_response.status_code == 200, score_response.text
        body = score_response.json()
        assert "score" in body
        assert "components" in body

    def test_compliance_score_requires_owner(self):
        headers = _auth_headers()
        project = _create_project(headers=headers)
        other_headers = _auth_headers()
        response = client.get(f"/api/compliance/{project['id']}/score", headers=other_headers)
        assert response.status_code == 403


class TestChatHistory:
    def test_chat_history_requires_auth(self):
        response = client.get(f"/api/chat/history/{uuid.uuid4()}")
        assert response.status_code == 401


class TestApplicationsEndpoints:
    def test_list_applications_empty(self):
        headers = _auth_headers()
        _create_project(headers=headers)
        response = client.get("/api/applications", headers=headers)
        assert response.status_code == 200
        assert response.json() == {"applications": []}

    def test_list_applications_requires_auth(self):
        response = client.get("/api/applications")
        assert response.status_code == 401


class TestSchemesEndpoints:
    def test_list_schemes_requires_auth(self):
        response = client.get("/api/schemes")
        assert response.status_code == 401

    def test_list_schemes_empty(self):
        headers = _auth_headers()
        response = client.get("/api/schemes", headers=headers)
        assert response.status_code == 200
        assert response.json() == {"schemes": []}


class TestBusinessIntelligenceEndpoints:
    def test_scheme_match_empty(self):
        headers = _auth_headers()
        response = client.post(
            "/api/schemes/match",
            json={
                "sector": "Textile",
                "state": "Maharashtra",
                "investment_amount": 1000000,
                "employees": 50,
            },
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json() == {"matches": []}

    def test_scheme_match_requires_auth(self):
        response = client.post(
            "/api/schemes/match",
            json={"sector": "Textile", "state": "Maharashtra", "investment_amount": 1000000, "employees": 50},
        )
        assert response.status_code == 401

    def test_simulate_capacity_expansion(self):
        headers = _auth_headers()
        response = client.post(
            "/api/simulate/scenario",
            json={
                "scenario_type": "capacity_expansion",
                "project_data": {"capacity": 100, "sector": "Manufacturing"},
                "parameters": {"new_capacity": 250},
            },
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["scenario"] == "capacity_expansion"
        assert body["capacity_increase_percent"] == 150.0
        assert len(body["changes"]["new_approvals_required"]) > 0

    def test_simulate_requires_auth(self):
        response = client.post(
            "/api/simulate/scenario",
            json={"scenario_type": "capacity_expansion", "project_data": {}, "parameters": {}},
        )
        assert response.status_code == 401

    def test_simulate_location_route_no_500(self):
        headers = _auth_headers()
        project = _create_project(headers=headers)
        response = client.get(
            f"/api/simulate/location/{project['id']}",
            params={"new_state": "Gujarat", "new_district": "Surat"},
            headers=headers,
        )
        assert response.status_code == 200, response.text

    def test_simulate_location_other_user_403(self):
        owner_headers = _auth_headers()
        project = _create_project(headers=owner_headers)
        other_headers = _auth_headers()
        response = client.get(
            f"/api/simulate/location/{project['id']}",
            params={"new_state": "Gujarat", "new_district": "Surat"},
            headers=other_headers,
        )
        assert response.status_code == 403

    def test_unknown_scenario_400(self):
        headers = _auth_headers()
        response = client.post(
            "/api/simulate/scenario",
            json={"scenario_type": "time_travel", "project_data": {}, "parameters": {}},
            headers=headers,
        )
        assert response.status_code == 400

    def test_compliance_score_route(self):
        headers = _auth_headers()
        project = _create_project(headers=headers)
        response = client.get(f"/api/compliance/{project['id']}/score", headers=headers)
        assert response.status_code == 200
        assert response.json()["score"] == 0

    def test_scheme_detail_missing_404(self):
        headers = _auth_headers()
        response = client.get("/api/schemes/nonexistent-scheme", headers=headers)
        assert response.status_code == 404