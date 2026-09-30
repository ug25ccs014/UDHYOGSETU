import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
_PASSWORD = "Password@123"


def _email(prefix="u"):
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


def _headers(email=None):
    email = _email(email or "u")
    payload = {
        "email": email,
        "name": "Incentive API User",
        "phone": "9876543210",
        "password": _PASSWORD,
        "role": "ENTREPRENEUR",
    }
    assert client.post("/api/auth/register", json=payload).status_code == 201
    response = client.post("/api/auth/login", json={"email": email, "password": _PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _project(headers):
    payload = {
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
        "employees": 50,
        "production_type": "continuous",
        "hazardous_materials": False,
        "has_boiler": True,
        "electricity_load": 350.0,
        "water_consumption": 2000.0,
        "pollution_potential": "medium",
        "building_type": "industrial",
    }
    response = client.post("/api/projects", json=payload, headers=headers)
    assert response.status_code == 200
    return response.json()


class TestIncentiveReadinessAPI:
    def test_requires_auth(self):
        project_id = uuid.uuid4()
        response = client.get(f"/api/schemes/projects/{project_id}/readiness")
        assert response.status_code == 401

    def test_owner_project_endpoint(self):
        headers = _headers()
        project = _project(headers)
        response = client.get(f"/api/schemes/projects/{project['id']}/readiness", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["project_id"] == project["id"]
        assert "matches" in body
        assert "note" in body

    def test_other_user_cannot_read_project_readiness(self):
        owner_headers = _headers("owner")
        project = _project(owner_headers)
        other_headers = _headers("other")
        response = client.get(f"/api/schemes/projects/{project['id']}/readiness", headers=other_headers)
        assert response.status_code == 403

    def test_missing_scheme_is_404(self):
        headers = _headers()
        project = _project(headers)
        response = client.get(
            f"/api/schemes/projects/{project['id']}/{uuid.uuid4()}/readiness",
            headers=headers,
        )
        assert response.status_code == 404

    def test_prepare_requires_existing_scheme(self):
        headers = _headers()
        project = _project(headers)
        response = client.post(
            f"/api/schemes/projects/{project['id']}/{uuid.uuid4()}/prepare",
            json={"document_ids": []},
            headers=headers,
        )
        assert response.status_code == 404
