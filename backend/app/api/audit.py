"""Audit trail view endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_officer
from app.core.database import get_db_session
from app.models import AuditLog

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs")
async def audit_logs(
    user: dict = Depends(require_officer),
    db: AsyncSession = Depends(get_db_session),
    limit: int = 100,
    user_id: str | None = None,
):
    """Return recent audit log entries (admin/supervisor surface)."""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(limit, 500))
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    rows = await db.execute(stmt)
    logs = rows.scalars().all()
    return {
        "logs": [
            {
                "id": str(l.id),
                "user_id": l.user_id,
                "action": l.action,
                "resource_type": l.resource_type,
                "resource_id": l.resource_id,
                "details": l.details,
                "ip_address": l.ip_address,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ],
        "count": len(logs),
    }