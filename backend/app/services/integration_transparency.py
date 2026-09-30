"""Truthful service-level government integration metadata."""

from __future__ import annotations

from app.integrations.integration_registry import SYSTEM_DEFINITIONS


def service_integration(service) -> dict:
    mode = (getattr(service, "application_mode", None) or "GUIDED").upper()
    is_demo = bool(getattr(service, "is_demo", False))
    gateway_system = getattr(service, "gateway_system", None)
    portal = getattr(service, "external_portal_url", None)

    if mode == "REDIRECT":
        return {
            "classification": "EXTERNAL_PORTAL",
            "label": "External Government Portal",
            "status": "REDIRECT",
            "source_label": "Official External Portal",
            "provider": "external",
            "is_simulated": False,
            "gateway_system": gateway_system,
            "external_portal_url": portal,
            "submission_handling": "external",
            "note": "UDYOGSETU prepares guidance only; the applicant completes submission on the official portal.",
        }

    if mode == "DEMO" or (is_demo and mode == "INTEGRATED"):
        return {
            "classification": "PROTOTYPE_SIMULATOR",
            "label": "Prototype Simulator",
            "status": "AVAILABLE",
            "source_label": "Prototype Simulator",
            "provider": "prototype",
            "is_simulated": True,
            "gateway_system": gateway_system,
            "external_portal_url": portal,
            "submission_handling": "simulated",
            "note": "This flow is simulated for the prototype. No government system is contacted.",
        }

    if mode == "GUIDED":
        return {
            "classification": "GUIDED_PROTOTYPE" if is_demo else "GUIDED_SUBMISSION",
            "label": "Guided Prototype" if is_demo else "Guided Submission",
            "status": "GUIDED",
            "source_label": "Prototype Guidance" if is_demo else "Guided / External Submission",
            "provider": "guided",
            "is_simulated": is_demo,
            "gateway_system": gateway_system,
            "external_portal_url": portal,
            "submission_handling": "external",
            "note": (
                "UDYOGSETU prepares the checklist and documents. This prototype does not transmit the submission to the authority."
                if is_demo
                else "UDYOGSETU prepares the checklist and documents; the authority remains the submission channel."
            ),
        }

    if mode == "INTEGRATED" and not is_demo:
        return {
            "classification": "FUTURE_AUTHORIZED_API",
            "label": "Authorized API — Not Connected",
            "status": "NOT_CONFIGURED",
            "source_label": "Future Authorized API",
            "provider": "authorized",
            "is_simulated": False,
            "gateway_system": gateway_system,
            "external_portal_url": portal,
            "submission_handling": "not_configured",
            "note": "An authorized government API connection is required before this flow can be called integrated.",
        }

    definition = SYSTEM_DEFINITIONS.get((gateway_system or "").lower())
    return {
        "classification": "UNKNOWN",
        "label": "Integration Configuration Required",
        "status": "NOT_CONFIGURED",
        "source_label": "Configuration Required",
        "provider": "unknown",
        "is_simulated": False,
        "gateway_system": gateway_system,
        "external_portal_url": portal or (definition.official_portal if definition else None),
        "submission_handling": "not_configured",
        "note": "The service mode does not map to a configured integration path.",
    }
