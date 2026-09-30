"""AI observability API (spec §34).

Read-only aggregate metrics about AI/LLM interactions. Restricted to
OFFICER / ADMIN. Does not expose sensitive content.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.services.ai_observability import AIObservability

router = APIRouter(prefix="/observability", tags=["observability"])

_MODERATOR_ROLES = {"OFFICER", "ADMIN"}


@router.get("/ai/summary")
async def ai_summary(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    role = user.get("role")
    if role not in _MODERATOR_ROLES:
        raise HTTPException(status_code=403, detail="Officer or Admin access required")
    return await AIObservability(db).summary()
