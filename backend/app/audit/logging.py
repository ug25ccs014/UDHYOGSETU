import logging
import uuid as uuid_mod

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog

logger = logging.getLogger(__name__)


def setup_audit_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


async def log_audit(
    db: AsyncSession,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    details: dict | None = None,
    ip_address: str | None = None,
):
    # resource_id is a UUID column; tolerate arbitrary path segments.
    parsed_id = None
    if resource_id:
        try:
            parsed_id = uuid_mod.UUID(str(resource_id))
        except (ValueError, AttributeError, TypeError):
            parsed_id = None

    audit_log = AuditLog(
        user_id=uuid_mod.UUID(str(user_id)) if user_id else None,
        action=action,
        resource_type=resource_type,
        resource_id=parsed_id,
        details=details or {},
        ip_address=ip_address,
    )
    db.add(audit_log)
    await db.commit()
    logger.info("AUDIT: %s on %s %s by %s", action, resource_type, resource_id, user_id)
