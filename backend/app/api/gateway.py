"""REST router over the government gateway (mock + adapters) and health."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import require_auth, require_officer
from app.services.gateway_service import GatewayService

router = APIRouter(prefix="/gateway", tags=["government-gateway"])


def _gateway() -> GatewayService:
    return GatewayService()


@router.get("/systems")
async def list_systems(user: dict = Depends(require_officer)):
    catalog = GatewayService().catalog()
    return {"systems": [item["system"] for item in catalog], "catalog": catalog}


@router.get("/catalog")
async def integration_catalog(user: dict = Depends(require_auth)):
    """Transparent integration catalog for applicants and officers."""
    return GatewayService().catalog()


@router.get("/health")
async def gateway_health(
    user: dict = Depends(require_officer),
):
    """Per-system availability / latency dashboard data."""
    return await GatewayService().system_health(force=True)


@router.get("/{system}/services")
async def system_services(
    system: str,
    user: dict = Depends(require_officer),
):
    try:
        return await GatewayService().get_services(system)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{system}/status/{application_id}")
async def application_status(
    system: str,
    application_id: str,
    user: dict = Depends(require_officer),
):
    return await GatewayService().get_status(system, application_id)


@router.post("/{system}/submit")
async def submit_application(
    system: str,
    application_data: dict,
    user: dict = Depends(require_officer),
):
    try:
        return await GatewayService().submit(system, application_data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/verify/{kind}/{value}")
async def verify_business(
    kind: str,
    value: str,
    user: dict = Depends(require_officer),
):
    """Verify a GSTIN/PAN/Udyam or scheme eligibility against mock registry."""
    return await GatewayService().verify(kind, value)