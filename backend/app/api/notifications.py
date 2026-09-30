"""Owner-scoped notification center API."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.notifications.service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    unread_only: bool = False,
    category: str | None = None,
    severity: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    service = NotificationService(db)
    notifications = await service.list_for_user(
        user["sub"],
        unread_only=unread_only,
        category=category,
        severity=severity,
        limit=limit,
        offset=offset,
    )
    total = await service.total_for_user(
        user["sub"],
        unread_only=unread_only,
        category=category,
        severity=severity,
    )
    return {
        "notifications": [service.serialize(n) for n in notifications],
        "unread": await service.unread_count(user["sub"]),
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + len(notifications) < total,
    }


@router.get("/summary")
async def notification_summary(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    return await NotificationService(db).summary(user["sub"])


@router.get("/unread-count")
async def unread_count(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    return {"unread": await NotificationService(db).unread_count(user["sub"])}


@router.post("/read-all")
async def mark_all_read(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    category: str | None = None,
):
    count = await NotificationService(db).mark_all_read(user["sub"], category=category)
    return {"status": "read", "marked": count}


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    service = NotificationService(db)
    ok = await service.mark_read(user["sub"], notification_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"status": "read", "notification_id": notification_id}
