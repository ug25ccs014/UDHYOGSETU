"""Application preparation APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.schemas import ApplicationPreparationUpdate
from app.services.application_preparation import ApplicationPreparationService

router = APIRouter(prefix="/applications", tags=["application-preparation"])


@router.get("/{application_id}/preparation")
async def get_application_preparation(
    application_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await ApplicationPreparationService(db).get(application_id, UUID(user["sub"]))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{application_id}/preparation")
async def save_application_preparation(
    application_id: str,
    payload: ApplicationPreparationUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await ApplicationPreparationService(db).save(
            application_id,
            UUID(user["sub"]),
            overrides=payload.overrides,
            reset_fields=payload.reset_fields,
            document_ids=payload.document_ids,
            mark_prepared=payload.mark_prepared,
        )
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() or "not owned" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message) from exc
