"""Government API Gateway service.

Routes requests to the correct system adapter, applies retry + timeout,
polls status, and monitors system health so the officer dashboard can show
per-system reliability.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from app.integrations.government_adapters import GovernmentAPIGateway
from app.integrations.mock_gov_api import get_mock_gov_api

logger = logging.getLogger(__name__)


class GatewayService:
    """Single facade over government integration providers.

    The default provider is the bundled prototype simulator. An authorized
    deployment can inject real adapter instances without changing route callers.
    """

    def __init__(self, gateway: GovernmentAPIGateway | None = None):
        self.gateway = gateway or GovernmentAPIGateway()
        self._health: dict[str, dict] = {}
        self._last_check: float = 0.0

    # ------------------------------------------------------------------
    # Transparency / discovery
    # ------------------------------------------------------------------
    def descriptor(self, system: str) -> dict:
        return self.gateway.descriptor(system)

    def catalog(self) -> dict:
        systems = self.gateway.catalog()
        simulated = sum(1 for item in systems if item["is_simulated"])
        configured = sum(1 for item in systems if item["status"] in {"AVAILABLE", "CONNECTED"})
        return {
            "provider": self.gateway.provider,
            "systems": systems,
            "summary": {
                "total_systems": len(systems),
                "configured_systems": configured,
                "simulated_systems": simulated,
                "authorized_systems": sum(1 for item in systems if item["classification"] == "AUTHORIZED_API"),
                "future_authorized_systems": sum(1 for item in systems if item["classification"] == "FUTURE_AUTHORIZED_API"),
                "external_portal_systems": sum(1 for item in systems if item["classification"] == "EXTERNAL_PORTAL"),
            },
            "disclaimer": (
                "Government connectivity is explicitly classified per system. "
                "Prototype Simulator responses are not live government data; "
                "authorized API connections require deployment-time authorization and adapter configuration."
            ),
        }

    async def get_services(self, system: str) -> dict:
        descriptor = self.descriptor(system)
        data = await self._with_retry(lambda: self.gateway.get_services(system), system)
        return self._decorate(data, system, "service_discovery", descriptor)

    # ------------------------------------------------------------------
    # Status / submission with retry + timeout
    # ------------------------------------------------------------------
    async def get_status(self, system: str, application_id: str) -> dict:
        descriptor = self.descriptor(system)
        result = await self._with_retry(
            lambda: self.gateway.get_application_status(system, application_id),
            system,
        )
        return self._decorate(result, system, "status", descriptor)

    async def submit(self, system: str, application_data: dict) -> dict:
        descriptor = self.descriptor(system)
        result = await self._with_retry(
            lambda: self.gateway.submit_application(system, application_data),
            system,
        )
        return self._decorate(result, system, "submission", descriptor)

    async def get_all_statuses(self, application_ids: dict) -> dict:
        results = {}
        for system, app_id in application_ids.items():
            results[system] = await self.get_status(system, app_id)
        return results

    async def verify(self, kind: str, value: str) -> dict:
        """Route prototype business-verification lookups with explicit source metadata."""
        if self.gateway.provider != "prototype":
            return {
                "data": None,
                "status": "NOT_CONFIGURED",
                "integration": {
                    "classification": "FUTURE_AUTHORIZED_API",
                    "source_label": "Future Authorized API",
                    "is_simulated": False,
                    "provider": self.gateway.provider,
                    "note": "No authorized identity-verification adapter is configured.",
                },
            }
        from app.integrations.mock_gov_api import get_mock_gov_api
        mock = get_mock_gov_api()
        if kind == "gstin":
            result = await mock.verify_gstin(value)
        elif kind == "pan":
            result = await mock.verify_pan(value)
        elif kind == "udyam":
            result = await mock.verify_udyam(value)
        elif kind == "scheme":
            result = await mock.check_scheme_eligibility(value, {})
        elif kind == "clearance":
            result = await mock.check_clearance(value, {})
        else:
            return {"data": None, "message": f"Unknown verification kind: {kind}"}
        result["integration"] = {
            "classification": "PROTOTYPE_SIMULATOR",
            "source_label": "Prototype Verification",
            "is_simulated": True,
            "provider": "prototype",
            "note": "No live government verification service is contacted by this prototype.",
        }
        return result

    @staticmethod
    def _decorate(payload: dict, system: str, operation: str, descriptor: dict) -> dict:
        if not isinstance(payload, dict):
            payload = {"data": payload}
        return {
            **payload,
            "integration": {
                **descriptor,
                "operation": operation,
            },
        }

    async def _with_retry(
        self,
        operation: Callable[[], Awaitable[Any]],
        system: str,
        retries: int = 2,
        timeout: float = 10.0,
    ) -> Any:
        attempt = 0
        while True:
            try:
                result = await asyncio.wait_for(operation(), timeout=timeout)
                self._record_health(system, ok=True, latency=0.5)
                return result
            except Exception as exc:  # noqa: BLE001
                attempt += 1
                self._record_health(system, ok=False, latency=1.0)
                if attempt > retries:
                    logger.warning("Gateway %s failed after %d attempts: %s", system, attempt, exc)
                    return {"system": system, "error": str(exc), "status": "UNAVAILABLE"}
                await asyncio.sleep(0.2 * attempt)

    def _record_health(self, system: str, ok: bool, latency: float):
        entry = self._health.setdefault(system, {"ok": 0, "total": 0, "latency": 0.0})
        entry["total"] += 1
        entry["ok"] += int(ok)
        entry["latency"] = (entry["latency"] * (entry["total"] - 1) + latency) / entry["total"]

    # ------------------------------------------------------------------
    # System health / connectivity transparency
    # ------------------------------------------------------------------
    async def system_health(self, force: bool = False) -> dict:
        now = time.time()
        if not force and self._last_check and (now - self._last_check) < 30:
            return self._snapshot()
        self._last_check = now
        for system in self.gateway.catalog():
            key = system["system"]
            descriptor = self.descriptor(key)
            if descriptor["status"] in {"AVAILABLE", "CONNECTED"} and descriptor["supports_services"]:
                try:
                    started = time.perf_counter()
                    await asyncio.wait_for(self.gateway.get_services(key), timeout=5)
                    self._record_health(key, ok=True, latency=time.perf_counter() - started)
                except Exception:  # noqa: BLE001 - per-system probe must not block others
                    self._record_health(key, ok=False, latency=1.0)
            else:
                # This is not a network health claim: it reflects whether a configured adapter exists.
                self._health.setdefault(key, {"ok": 0, "total": 0, "latency": 0.0})
        return self._snapshot()

    def _snapshot(self) -> dict:
        systems = {}
        for descriptor in self.gateway.catalog():
            name = descriptor["system"]
            entry = self._health.get(name, {"ok": 0, "total": 0, "latency": 0.0})
            if descriptor["classification"] == "PROTOTYPE_SIMULATOR":
                ok_rate = (entry["ok"] / entry["total"]) if entry["total"] else 1.0
                runtime_status = "HEALTHY" if ok_rate >= 0.9 else ("DEGRADED" if ok_rate >= 0.5 else "DOWN")
            elif descriptor["status"] == "CONNECTED":
                runtime_status = "CONNECTED"
                ok_rate = (entry["ok"] / entry["total"]) if entry["total"] else 1.0
            else:
                runtime_status = "NOT_CONFIGURED"
                ok_rate = 0.0
            systems[name] = {
                **descriptor,
                "runtime_status": runtime_status,
                "availability_pct": round(ok_rate * 100, 1),
                "avg_latency_ms": round(entry["latency"] * 1000, 1) if entry["total"] else None,
                "probes": entry["total"],
            }
        return {
            "provider": self.gateway.provider,
            "systems": systems,
            "checked_at": datetime_iso(),
            "disclaimer": (
                "Prototype system health measures simulator availability only. "
                "It does not indicate availability of a live government portal."
            ),
        }


def datetime_iso() -> str:
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"