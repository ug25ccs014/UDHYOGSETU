"""RBAC / authorization regression tests.

Verifies that Officer and Admin surfaces are role-restricted, public
self-registration cannot grant privileged roles, and object-level and
JWT-integrity protections hold.
"""

import uuid

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app

client = TestClient(app)


def _unique_email(prefix="rbac"):
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


_PASSWORD = "Password@123"


def _register_entrepreneur(email=None):
    payload = {
        "email": email or _unique_email(),
        "name": "RBAC User",
        "phone": "9876543210",
        "password": _PASSWORD,
        "role": "ENTREPRENEUR",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _token_for(email):
    response = client.post("/api/auth/login", json={"email": email, "password": _PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _auth(email):
    return {"Authorization": f"Bearer {_token_for(email)}"}


# ---------------------------------------------------------------------------
# Self-service registration cannot grant privileged roles
# ---------------------------------------------------------------------------
class TestPrivilegedSelfRegistrationBlocked:
    def test_register_as_admin_rejected(self):
        payload = {
            "email": _unique_email(),
            "name": "Wannabe Admin",
            "phone": "9876543210",
            "password": _PASSWORD,
            "role": "ADMIN",
        }
        response = client.post("/api/auth/register", json=payload)
        assert response.status_code == 403, response.text

    def test_register_as_officer_rejected(self):
        payload = {
            "email": _unique_email(),
            "name": "Wannabe Officer",
            "phone": "9876543210",
            "password": _PASSWORD,
            "role": "OFFICER",
        }
        response = client.post("/api/auth/register", json=payload)
        assert response.status_code == 403, response.text

    def test_register_as_entrepreneur_allowed(self):
        user = _register_entrepreneur()
        assert user["role"] == "ENTREPRENEUR"


# ---------------------------------------------------------------------------
# Role tampering via request body is rejected
# ---------------------------------------------------------------------------
class TestRequestBodyRoleManipulation:
    def test_register_upper_case_admin_rejected(self):
        payload = {
            "email": _unique_email(),
            "name": "Wannabe",
            "phone": "9876543210",
            "password": _PASSWORD,
            "role": "admin",
        }
        # "admin" is not a valid enum value -> 422; the point is it is never accepted
        response = client.post("/api/auth/register", json=payload)
        assert response.status_code in (403, 422)


# ---------------------------------------------------------------------------
# Entrepreneur cannot reach officer/admin surfaces
# ---------------------------------------------------------------------------
class TestOfficerEndpointsRoleRestricted:
    def test_officer_overview_requires_moderator(self):
        ent = _register_entrepreneur()
        h = _auth(ent["email"])
        response = client.get("/api/officer/full", headers=h)
        assert response.status_code == 403

    def test_officer_overview_no_token(self):
        response = client.get("/api/officer/full")
        assert response.status_code == 401

    def test_officer_overview_allows_officer(self):
        # Provision an OFFICER directly in the DB (only trusted path may create one).
        import asyncio

        from app.core.database import AsyncSessionLocal
        from app.core.security import hash_password
        from app.models import User, UserRole

        async def _provision_officer_and_call():
            async with AsyncSessionLocal() as db:
                email = _unique_email()
                db.add(User(
                    email=email, name="Officer",
                    phone="9876543210",
                    password_hash=hash_password(_PASSWORD),
                    role=UserRole.OFFICER, is_active=True,
                ))
                await db.commit()
            token = create_access_token(
                data={"sub": str(uuid.uuid4()), "email": "officer@x", "role": "OFFICER"}
            )
            return {"Authorization": f"Bearer {token}"}

        h = asyncio.run(_provision_officer_and_call())
        response = client.get("/api/officer/full", headers=h)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Audit logs are moderator-only
# ---------------------------------------------------------------------------
class TestAuditLogsRoleRestricted:
    def test_audit_logs_requires_moderator(self):
        ent = _register_entrepreneur()
        response = client.get("/api/audit/logs", headers=_auth(ent["email"]))
        assert response.status_code == 403

    def test_audit_logs_no_token(self):
        response = client.get("/api/audit/logs")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Gateway surfaces are moderator-only
# ---------------------------------------------------------------------------
class TestGatewayRoleRestricted:
    def test_gateway_health_requires_moderator(self):
        ent = _register_entrepreneur()
        response = client.get("/api/gateway/health", headers=_auth(ent["email"]))
        assert response.status_code == 403

    def test_gateway_health_no_token(self):
        response = client.get("/api/gateway/health")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Unauthenticated government status endpoint is now gated
# ---------------------------------------------------------------------------
class TestGovernmentStatusAuth:
    def test_government_status_requires_auth(self):
        response = client.get("/api/regulatory/government/maitri/status/any-id")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tampered JWT is rejected (role claim manipulation)
# ---------------------------------------------------------------------------
class TestJwtTampering:
    def test_tampered_role_claim_rejected(self):
        ent = _register_entrepreneur()
        token = _token_for(ent["email"])
        parts = token.split(".")
        # Replace the payload with an ADMIN role but keep the original signature.
        import base64
        import json as _json
        forged_payload = base64.urlsafe_b64encode(
            _json.dumps({"role": "ADMIN", "sub": "0"}).encode()
        ).rstrip(b"=").decode()
        forged = f"{parts[0]}.{forged_payload}.{parts[2]}"
        response = client.get("/api/officer/full", headers={"Authorization": f"Bearer {forged}"})
        assert response.status_code == 401

    def test_malformed_token_rejected(self):
        response = client.get("/api/officer/full", headers={"Authorization": "Bearer garbage"})
        assert response.status_code == 401