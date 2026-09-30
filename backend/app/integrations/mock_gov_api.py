"""Mock Government API layer.

Implements realistic HTTP-style endpoints (tokens, envelope responses,
correlation ids, timestamps) for the government systems that UdyogSetu
integrates with, so the frontend and integration tests see the same
contracts a live system would provide. Replacements pointed at real systems
swap the backend of these endpoints without changing the API shape.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# In-memory token store keyed by system.
_TOKENS: dict[str, str] = {}

_SI_DEMO_STATUS = {
    "maitri": "UNDER_REVIEW",
    "mpcb": "QUERY_RAISED",
    "boiler": "UNDER_REVIEW",
    "fire": "APPROVED",
    "labour": "APPROVED",
}


def _prototype_scenario() -> str:
    try:
        from app.core.config import settings
        return (settings.GOVERNMENT_PROTOTYPE_SCENARIO or "si_demo").strip().lower()
    except Exception:
        return "si_demo"


def _stable_id(system: str, payload: dict | None = None) -> str:
    data = payload or {}
    reference = data.get("application_key") or data.get("application_id")
    if reference is None:
        reference = json.dumps(data, sort_keys=True, default=str, separators=(",", ":"))
    digest = hashlib.sha256(f"udyogsetu:{system}:{reference}".encode()).hexdigest()[:10].upper()
    return f"{system.upper()}-{digest}"


def _envelope(payload: dict, system: str, message: str | None = None) -> dict:
    """Wrap a payload in the shared response envelope."""
    return {
        "data": payload,
        "meta": {
            "system": system,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": str(uuid.uuid4()),
        },
        "message": message,
    }


def _status_pool(system: str) -> list[str]:
    if system == "mpcb":
        return ["NOT_STARTED", "SUBMITTED", "QUERY_RAISED", "UNDER_REVIEW", "APPROVED", "REJECTED"]
    return ["NOT_STARTED", "SUBMITTED", "UNDER_REVIEW", "QUERY_RAISED", "APPROVED"]


def _pick_status(system: str, app_id: str) -> str:
    digest = sum(ord(c) for c in f"{system}:{app_id}")
    pool = _status_pool(system)
    return pool[digest % len(pool)]


class MockGovAPI:
    """Stateless request handlers for the mock government systems."""

    SYSTEMS = ("maitri", "mpcb", "midc", "boiler", "fire", "labour", "gst", "esic", "dea")

    def __init__(self, base_url: str = "http://mock-gov.local"):
        self.base_url = base_url

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------
    async def obtain_token(self, system: str, client_id: str, client_secret: str) -> dict:
        token = "tok_" + uuid.uuid4().hex[:24]
        _TOKENS[system] = token
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "system": system,
        }

    async def validate_token(self, system: str, token: str) -> bool:
        return _TOKENS.get(system) == token

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------
    async def list_services(self, system: str) -> dict:
        services = {
            "maitri": [
                {"id": "factory_license", "name": "Factory License", "department": "Factory", "sla_days": 30},
                {"id": "unit_registration", "name": "Micro & Small Enterprise (Udyam) Registration", "department": "DIC", "sla_days": 15},
            ],
            "mpcb": [
                {"id": "consent_establish", "name": "Consent to Establish", "department": "MPCB", "sla_days": 60},
                {"id": "consent_operate", "name": "Consent to Operate", "department": "MPCB", "sla_days": 60},
            ],
            "midc": [
                {"id": "plot_allotment", "name": "Industrial Plot Allotment", "department": "MIDC", "sla_days": 90},
                {"id": "plot_occupancy", "name": "Occupancy Certificate", "department": "MIDC", "sla_days": 45},
            ],
            "boiler": [
                {"id": "boiler_registration", "name": "Boiler Registration", "department": "Boiler Safety", "sla_days": 45},
                {"id": "boiler_renewal", "name": "Boiler Renewal", "department": "Boiler Safety", "sla_days": 30},
            ],
            "fire": [
                {"id": "fire_noc", "name": "Fire No Objection Certificate", "department": "Fire Services", "sla_days": 30},
                {"id": "fire_inspection", "name": "Fire Safety Inspection", "department": "Fire Services", "sla_days": 15},
            ],
            "labour": [
                {"id": "labour_license", "name": "Labour License", "department": "Labour", "sla_days": 21},
                {"id": "esi_registration", "name": "ESI Registration", "department": "ESIC", "sla_days": 30},
            ],
            "gst": [
                {"id": "gst_registration", "name": "GST Registration", "department": "GST", "sla_days": 7},
            ],
            "esic": [
                {"id": "esi_registration", "name": "ESI Registration", "department": "ESIC", "sla_days": 30},
            ],
            "dea": [
                {"id": "ie_code", "name": "Import Export Code", "department": "DGFT/DEA", "sla_days": 10},
            ],
        }
        return _envelope(services.get(system, []), system)

    # ------------------------------------------------------------------
    # Application lifecycle
    # ------------------------------------------------------------------
    async def get_application_status(self, system: str, application_id: str) -> dict:
        status = _SI_DEMO_STATUS.get(system) if _prototype_scenario() in {"si_demo", "si_demo_v1", "demo"} else _pick_status(system, application_id)
        payload = {
            "application_id": application_id,
            "system": system,
            "status": status,
            "submitted_at": (datetime.utcnow() - timedelta(days=10)).isoformat() + "Z",
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "sla_days": 30,
            "days_elapsed": 10,
        }
        if status == "QUERY_RAISED":
            payload["query"] = "Please provide ETP capacity details and water meter reading."
        if status == "APPROVED":
            payload["approved_date"] = (datetime.utcnow() - timedelta(days=2)).isoformat() + "Z"
            payload["certificate_url"] = f"{self.base_url}/downloads/{system}/{application_id}/certificate.pdf"
        return _envelope(payload, system)

    async def submit_application(self, system: str, application_data: dict) -> dict:
        application_id = _stable_id(system, application_data)
        payload = {
            "application_id": application_id,
            "system": system,
            "status": "SUBMITTED",
            "submitted_at": datetime.utcnow().isoformat() + "Z",
            "sla_days": application_data.get("sla_days", 30),
            "message": f"Application submitted successfully to {system.upper()}",
        }
        return _envelope(payload, system)

    async def upload_document(self, system: str, application_id: str, doc_type: str) -> dict:
        return _envelope(
            {"application_id": application_id, "document": doc_type, "accepted": True, "pages": 2},
            system,
            "Document uploaded successfully",
        )

    # ------------------------------------------------------------------
    # Verification lookups (spec §19)
    # ------------------------------------------------------------------
    async def verify_gstin(self, gstin: str) -> dict:
        valid = bool(gstin and len(gstin) == 15)
        return _envelope(
            {
                "gstin": gstin,
                "valid": valid,
                "trade_name": "Sample Manufacturing Co" if valid else None,
                "registration_date": "2021-04-01" if valid else None,
                "status": "ACTIVE" if valid else "INVALID",
            },
            "gst",
        )

    async def verify_pan(self, pan: str) -> dict:
        valid = bool(pan and len(pan) == 10)
        return _envelope(
            {"pan": pan, "valid": valid, "name": "Sample Proprietor" if valid else None, "status": "ACTIVE" if valid else "INVALID"},
            "cbd",
        )

    async def verify_udyam(self, udyam_id: str) -> dict:
        return _envelope(
            {"udyam_id": udyam_id, "valid": bool(udyam_id), "registered": True, "type": "MICRO"},
            "maa",
        )

    async def check_scheme_eligibility(self, scheme_code: str, business: dict) -> dict:
        score = 50 + (int(hashlib.sha256(f"scheme:{scheme_code}:{json.dumps(business, sort_keys=True, default=str)}".encode()).hexdigest()[:8], 16) % 51)
        return _envelope(
            {
                "scheme_code": scheme_code,
                "eligible": score >= 60,
                "eligibility_score": score,
                "points": {"zoning": 20, "industry": 25, "turnover": 15, "employment": 30},
                "reasons": ["Meets MSME definition", "Located in notified industrial area"],
            },
            "schemes",
        )

    async def check_clearance(self, system: str, params: dict) -> dict:
        return _envelope(
            {"system": system, "param_count": len(params), "status": "INSPECTION_SCHEDULED", "suggested_date": (datetime.utcnow() + timedelta(days=3)).date().isoformat()},
            system,
        )


_mock_gov = MockGovAPI()


def get_mock_gov_api() -> MockGovAPI:
    return _mock_gov