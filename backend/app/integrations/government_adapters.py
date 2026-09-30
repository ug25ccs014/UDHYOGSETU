import hashlib
import json
from typing import ClassVar
from abc import ABC, abstractmethod
from datetime import datetime, timedelta


def _prototype_scenario() -> str:
    try:
        from app.core.config import settings
        return (settings.GOVERNMENT_PROTOTYPE_SCENARIO or "si_demo").strip().lower()
    except Exception:
        return "si_demo"


_SI_DEMO_STATUS = {
    "maitri": "UNDER_REVIEW",
    "mpcb": "QUERY_RAISED",
    "midc": "APPROVED",
    "boiler": "UNDER_REVIEW",
    "fire": "APPROVED",
    "labour": "APPROVED",
}


def _stable_id(system: str, payload: dict | None = None) -> str:
    data = payload or {}
    reference = data.get("application_key") or data.get("application_id")
    if reference is None:
        reference = json.dumps(data, sort_keys=True, default=str, separators=(",", ":"))
    digest = hashlib.sha256(f"udyogsetu:{system}:{reference}".encode()).hexdigest()[:10].upper()
    return f"{system.upper()}-{digest}"


def _deterministic_status(system: str, application_id: str, pool: list[str]) -> str:
    if _prototype_scenario() in {"si_demo", "si_demo_v1", "demo"} and system in _SI_DEMO_STATUS:
        return _SI_DEMO_STATUS[system]
    digest = int(hashlib.sha256(f"{system}:{application_id}".encode()).hexdigest()[:12], 16)
    return pool[digest % len(pool)]


class GovernmentIntegrationAdapter(ABC):
    """Base interface for government system adapters.

    Current concrete implementations are prototype simulators. Authorized
    production adapters can implement the same interface and be injected into
    ``GovernmentAPIGateway`` without changing downstream services.
    """

    system_key: ClassVar[str] = ""
    display_name: ClassVar[str] = ""
    is_simulated: ClassVar[bool] = False

    @abstractmethod
    async def authenticate(self):
        """Authenticate with government system"""
    
    @abstractmethod
    async def get_services(self) -> list[dict]:
        """Get available services"""
    
    @abstractmethod
    async def get_application_status(self, application_id: str) -> dict:
        """Get application status"""
    
    @abstractmethod
    async def submit_application(self, application_data: dict) -> dict:
        """Submit application"""


class MaitriAdapter(GovernmentIntegrationAdapter):
    system_key = "maitri"
    display_name = "MAITRI"
    is_simulated = True
    """Adapter for MAITRI system integration"""
    
    async def authenticate(self):
        return {"status": "authenticated", "system": "MAITRI"}
    
    async def get_services(self) -> list[dict]:
        return [
            {"id": "factory_license", "name": "Factory License", "department": "Factory"},
            {"id": "building_approval", "name": "Building Approval", "department": "Building"},
        ]
    
    async def get_application_status(self, application_id: str) -> dict:
        statuses = ['NOT_STARTED', 'SUBMITTED', 'UNDER_REVIEW', 'QUERY_RAISED', 'APPROVED']
        return {
            "application_id": application_id,
            "system": "MAITRI",
            "status": _deterministic_status("maitri", application_id, statuses),
            "submitted_at": (datetime.utcnow() - timedelta(days=10)).isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "sla_days": 30,
            "days_elapsed": 10,
        }
    
    async def submit_application(self, application_data: dict) -> dict:
        return {
            "application_id":  _stable_id("maitri", application_data),
            "status": "SUBMITTED",
            "submitted_at": datetime.utcnow().isoformat(),
            "message": "Application submitted successfully to MAITRI",
        }


class MpcbAdapter(GovernmentIntegrationAdapter):
    system_key = "mpcb"
    display_name = "MPCB"
    is_simulated = True
    """Adapter for MPCB (Maharashtra Pollution Control Board) integration"""
    
    async def authenticate(self):
        return {"status": "authenticated", "system": "MPCB"}
    
    async def get_services(self) -> list[dict]:
        return [
            {"id": "consent_establish", "name": "Consent to Establish", "department": "MPCB"},
            {"id": "consent_operate", "name": "Consent to Operate", "department": "MPCB"},
        ]
    
    async def get_application_status(self, application_id: str) -> dict:
        return {
            "application_id": application_id,
            "system": "MPCB",
            "status": _deterministic_status("mpcb", application_id, ["SUBMITTED", "QUERY_RAISED", "UNDER_REVIEW", "APPROVED"]),
            "query": "ETP capacity details required",
            "submitted_at": (datetime.utcnow() - timedelta(days=20)).isoformat(),
            "sla_days": 60,
            "days_elapsed": 20,
        }
    
    async def submit_application(self, application_data: dict) -> dict:
        return {
            "application_id": _stable_id("mpcb", application_data),
            "status": "SUBMITTED",
            "submitted_at": datetime.utcnow().isoformat(),
            "message": "Application submitted to MPCB for review",
        }


class MidcAdapter(GovernmentIntegrationAdapter):
    system_key = "midc"
    display_name = "MIDC"
    is_simulated = True
    """Adapter for MIDC (Maharashtra Industrial Development Corporation) integration"""
    
    async def authenticate(self):
        return {"status": "authenticated", "system": "MIDC"}
    
    async def get_services(self) -> list[dict]:
        return [
            {"id": "plot_allotment", "name": "Plot Allotment", "department": "MIDC"},
            {"id": "industrial_area", "name": "Industrial Area Services", "department": "MIDC"},
        ]
    
    async def get_application_status(self, application_id: str) -> dict:
        return {
            "application_id": application_id,
            "system": "MIDC",
            "status": _deterministic_status("midc", application_id, ["SUBMITTED", "UNDER_REVIEW", "APPROVED"]),
            "approved_date": (datetime.utcnow() - timedelta(days=5)).isoformat() if _deterministic_status("midc", application_id, ["SUBMITTED", "UNDER_REVIEW", "APPROVED"]) == "APPROVED" else None,
        }
    
    async def submit_application(self, application_data: dict) -> dict:
        return {
            "application_id": _stable_id("midc", application_data),
            "status": "SUBMITTED",
            "submitted_at": datetime.utcnow().isoformat(),
        }


class BoilerAdapter(GovernmentIntegrationAdapter):
    system_key = "boiler"
    display_name = "Boiler Safety"
    is_simulated = True
    """Adapter for Boiler Registration system integration"""
    
    async def authenticate(self):
        return {"status": "authenticated", "system": "Boiler"}
    
    async def get_services(self) -> list[dict]:
        return [
            {"id": "boiler_registration", "name": "Boiler Registration", "department": "Boiler Safety"},
        ]
    
    async def get_application_status(self, application_id: str) -> dict:
        return {
            "application_id": application_id,
            "system": "Boiler",
            "status": _deterministic_status("boiler", application_id, ["SUBMITTED", "UNDER_REVIEW", "QUERY_RAISED", "APPROVED"]),
            "submitted_at": (datetime.utcnow() - timedelta(days=5)).isoformat(),
            "expected_completion": (datetime.utcnow() + timedelta(days=10)).isoformat(),
        }
    
    async def submit_application(self, application_data: dict) -> dict:
        return {
            "application_id": _stable_id("boiler", application_data),
            "status": "SUBMITTED",
            "submitted_at": datetime.utcnow().isoformat(),
        }


class FireAdapter(GovernmentIntegrationAdapter):
    system_key = "fire"
    display_name = "Fire Services"
    is_simulated = True
    """Adapter for Fire Safety Department integration"""
    
    async def authenticate(self):
        return {"status": "authenticated", "system": "Fire"}
    
    async def get_services(self) -> list[dict]:
        return [
            {"id": "fire_permission", "name": "Fire Safety Permission", "department": "Fire"},
        ]
    
    async def get_application_status(self, application_id: str) -> dict:
        return {
            "application_id": application_id,
            "system": "Fire",
            "status": _deterministic_status("fire", application_id, ["SUBMITTED", "UNDER_REVIEW", "INSPECTION", "APPROVED"]),
            "inspection_date": (datetime.utcnow() + timedelta(days=3)).isoformat(),
        }
    
    async def submit_application(self, application_data: dict) -> dict:
        return {
            "application_id": _stable_id("fire", application_data),
            "status": "SUBMITTED",
            "submitted_at": datetime.utcnow().isoformat(),
        }


class LabourAdapter(GovernmentIntegrationAdapter):
    system_key = "labour"
    display_name = "Labour"
    is_simulated = True
    """Adapter for Labour Department integration"""
    
    async def authenticate(self):
        return {"status": "authenticated", "system": "Labour"}
    
    async def get_services(self) -> list[dict]:
        return [
            {"id": "labour_license", "name": "Labour License", "department": "Labour"},
            {"id": "esi_registration", "name": "ESI Registration", "department": "Labour"},
        ]
    
    async def get_application_status(self, application_id: str) -> dict:
        return {
            "application_id": application_id,
            "system": "Labour",
            "status": _deterministic_status("labour", application_id, ["SUBMITTED", "UNDER_REVIEW", "APPROVED"]),
            "approved_date": (datetime.utcnow() - timedelta(days=2)).isoformat(),
        }
    
    async def submit_application(self, application_data: dict) -> dict:
        return {
            "application_id": _stable_id("labour", application_data),
            "status": "SUBMITTED",
            "submitted_at": datetime.utcnow().isoformat(),
        }


class GovernmentAPIGateway:
    """Provider-aware registry/facade for government integrations.

    ``provider=prototype`` uses the bundled simulated adapters. ``provider=authorized``
    is intentionally inert unless explicit authorized adapter instances are injected.
    """

    def __init__(self, provider: str | None = None, authorized_adapters: dict | None = None):
        from app.core.config import settings
        from app.integrations.integration_registry import IntegrationRegistry, normalize_provider

        self.provider = normalize_provider(provider or settings.GOVERNMENT_INTEGRATION_PROVIDER or "prototype")
        self.prototype_adapters = {
            "maitri": MaitriAdapter(),
            "mpcb": MpcbAdapter(),
            "midc": MidcAdapter(),
            "boiler": BoilerAdapter(),
            "fire": FireAdapter(),
            "labour": LabourAdapter(),
        }
        self.authorized_adapters = authorized_adapters or {}
        self.adapters = self.authorized_adapters if self.provider == "authorized" else self.prototype_adapters
        self.registry = IntegrationRegistry(self.provider, self.adapters)

    def descriptor(self, system: str) -> dict:
        return self.registry.descriptor(system)

    def catalog(self, systems: list[str] | tuple[str, ...] | None = None) -> list[dict]:
        return self.registry.catalog(systems)

    def _adapter(self, system: str):
        key = (system or "").strip().lower()
        adapter = self.adapters.get(key)
        if not adapter:
            descriptor = self.descriptor(key)
            raise ValueError(
                f"No adapter configured for {key or 'unknown system'} "
                f"({descriptor['source_label']})."
            )
        return adapter

    async def get_services(self, system: str) -> list[dict]:
        return await self._adapter(system).get_services()

    async def get_application_status(self, system: str, application_id: str) -> dict:
        return await self._adapter(system).get_application_status(application_id)

    async def submit_application(self, system: str, application_data: dict) -> dict:
        return await self._adapter(system).submit_application(application_data)

    async def get_all_statuses(self, application_ids: dict) -> dict:
        results = {}
        for system, app_id in application_ids.items():
            try:
                results[system] = await self.get_application_status(system, app_id)
            except Exception as e:  # noqa: BLE001 - one provider failure must not block others
                results[system] = {"error": str(e), "status": "UNAVAILABLE"}
        return results


_DEPARTMENT_TO_SYSTEM = {
    "mpcb": "mpcb",
    "pollution": "mpcb",
    "factory": "maitri",
    "industrial safety": "maitri",
    "fire": "fire",
    "boiler": "boiler",
    "steam boilers": "boiler",
    "midc": "midc",
    "labour": "labour",
    "gst": "gst",
    "esic": "esic",
}


def system_for_department(department: str | None) -> str | None:
    """Map a department name onto a government integration system key."""
    if not department:
        return None
    lowered = department.lower()
    for token, system in _DEPARTMENT_TO_SYSTEM.items():
        if token in lowered:
            return system
    return None
