"""Government integration registry and transparency metadata.

The prototype intentionally keeps real government adapters out of the runtime.
This registry provides a stable seam for authorized adapters to be injected later
without changing callers, while making the current simulation boundary explicit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SystemDefinition:
    key: str
    name: str
    description: str
    official_portal: str | None = None


KNOWN_SYSTEMS: tuple[SystemDefinition, ...] = (
    SystemDefinition("maitri", "MAITRI", "Industrial approvals and factory-related services."),
    SystemDefinition("mpcb", "MPCB", "Environmental and pollution-control services."),
    SystemDefinition("midc", "MIDC", "Industrial land and estate services."),
    SystemDefinition("boiler", "Boiler Safety", "Steam boiler registration and safety services."),
    SystemDefinition("fire", "Fire Services", "Fire safety permissions and inspections."),
    SystemDefinition("labour", "Labour", "Labour licensing and establishment services."),
    SystemDefinition("gst", "GST", "GST registration and related tax services.", "https://www.gst.gov.in"),
    SystemDefinition("esic", "ESIC", "Employee State Insurance services.", "https://www.esic.gov.in"),
    SystemDefinition("dea", "DGFT / Trade", "Import/export and trade services.", "https://www.dgft.gov.in"),
)

SYSTEM_DEFINITIONS = {item.key: item for item in KNOWN_SYSTEMS}


SUPPORTED_PROVIDERS = {"prototype", "authorized"}
PROVIDER_ALIASES = {"mock": "prototype", "demo": "prototype"}


def normalize_provider(provider: str | None) -> str:
    """Normalize provider configuration and reject unsupported values early."""
    raw = (provider or "prototype").strip().lower()
    normalized = PROVIDER_ALIASES.get(raw, raw)
    if normalized not in SUPPORTED_PROVIDERS:
        raise ValueError(
            f"Unsupported government integration provider: {raw}. "
            f"Expected one of: {', '.join(sorted(SUPPORTED_PROVIDERS))}."
        )
    return normalized


class IntegrationRegistry:
    """Build transparent descriptors for prototype and future providers."""

    def __init__(self, provider: str, adapters: dict[str, Any] | None = None):
        self.provider = normalize_provider(provider)
        self.adapters = adapters or {}

    def descriptor(self, system: str) -> dict:
        key = (system or "").strip().lower()
        definition = SYSTEM_DEFINITIONS.get(
            key,
            SystemDefinition(key, key.upper() or "Unknown system", "Unregistered integration system."),
        )
        adapter = self.adapters.get(key)

        if self.provider == "authorized":
            if adapter is not None:
                return {
                    "system": key,
                    "display_name": definition.name,
                    "classification": "AUTHORIZED_API",
                    "status": "CONNECTED",
                    "provider": "authorized",
                    "source_label": "Authorized Government API",
                    "is_simulated": False,
                    "supports_services": bool(getattr(adapter, "get_services", None)),
                    "supports_status": bool(getattr(adapter, "get_application_status", None)),
                    "supports_submission": bool(getattr(adapter, "submit_application", None)),
                    "official_portal_url": definition.official_portal,
                    "note": "Connected through an authorized adapter configured by the deployment.",
                }
            return {
                "system": key,
                "display_name": definition.name,
                "classification": "FUTURE_AUTHORIZED_API",
                "status": "NOT_CONFIGURED",
                "provider": "authorized",
                "source_label": "Future Authorized API",
                "is_simulated": False,
                "supports_services": False,
                "supports_status": False,
                "supports_submission": False,
                "official_portal_url": definition.official_portal,
                "note": "No authorized adapter is configured for this system.",
            }

        if adapter is None and definition.official_portal:
            return {
                "system": key,
                "display_name": definition.name,
                "classification": "EXTERNAL_PORTAL",
                "status": "PORTAL_AVAILABLE",
                "provider": "external",
                "source_label": "Official External Portal",
                "is_simulated": False,
                "supports_services": False,
                "supports_status": False,
                "supports_submission": False,
                "official_portal_url": definition.official_portal,
                "note": "This system is represented through its official external portal until an authorized API adapter is connected.",
            }

        if adapter is not None:
            return {
                "system": key,
                "display_name": definition.name,
                "classification": "PROTOTYPE_SIMULATOR",
                "status": "AVAILABLE",
                "provider": "prototype",
                "source_label": "Prototype Simulator",
                "is_simulated": True,
                "supports_services": bool(getattr(adapter, "get_services", None)),
                "supports_status": bool(getattr(adapter, "get_application_status", None)),
                "supports_submission": bool(getattr(adapter, "submit_application", None)),
                "official_portal_url": definition.official_portal,
                "note": "Prototype-only simulation. No government system is contacted.",
            }

        return {
            "system": key,
            "display_name": definition.name,
            "classification": "FUTURE_AUTHORIZED_API",
            "status": "NOT_CONFIGURED",
            "provider": "prototype",
            "source_label": "Future Authorized API",
            "is_simulated": False,
            "supports_services": False,
            "supports_status": False,
            "supports_submission": False,
            "official_portal_url": definition.official_portal,
            "note": "This system has no prototype adapter and is reserved for future authorized integration or external-portal handling.",
        }

    def catalog(self, systems: list[str] | tuple[str, ...] | None = None) -> list[dict]:
        keys = systems or tuple(SYSTEM_DEFINITIONS.keys())
        return [self.descriptor(key) for key in keys]
