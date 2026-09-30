"""SIH demo readiness API."""
from fastapi import APIRouter, Depends

from app.api.deps import require_auth
from app.core.database import get_db_session
from app.services.demo_readiness import DemoReadinessService

router = APIRouter(prefix="/demo", tags=["demo"] )


@router.get("/readiness")
async def demo_readiness(user: dict = Depends(require_auth), db = Depends(get_db_session)):
    return await DemoReadinessService(db).inspect(user["sub"])
