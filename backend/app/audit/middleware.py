"""ASGI/HTTP middleware that records auditable state-changing actions.

It runs after the handler and persists an AuditLog row (on its own session
so failures never break the request) for any authenticated mutation against
the API: POST/PUT/PATCH/DELETE. Read-only GETs are not recorded.
"""

from __future__ import annotations

import logging

from fastapi import Request

from app.core.security import verify_jwt

logger = logging.getLogger(__name__)

_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
# Skip internal/health/mock-verification noise.
_EXCLUDED_PREFIXES = ("/health", "/docs", "/redoc", "/openapi.json", "/gateway/verify")


def _client_ip(request: Request) -> str:
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


async def _persist(db, user_id: str, action: str, resource_type: str, resource_id: str, details: dict, ip: str):
    try:
        from app.audit.logging import log_audit
        await log_audit(
            db,
            user_id=str(user_id),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip,
        )
    except Exception:  # noqa: BLE001
        logger.warning("Failed to write audit log for %s", action)


async def audit_logging_middleware(request: Request, call_next):
    response = await call_next(request)
    try:
        if request.method not in _MUTATING_METHODS:
            return response
        path = request.url.path
        if any(path.startswith(p) for p in _EXCLUDED_PREFIXES):
            return response

        user = await verify_jwt(request)
        # Record only authenticated actions; anonymous mutating endpoints
        # (e.g. /auth/register) are intentionally not attribution-recorded.
        if not user:
            return response

        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            # resource_type/id inferred from the path (e.g. /api/documents/{id}/validate)
            segments = [s for s in path.split("/") if s]
            resource_type = segments[2] if len(segments) > 2 else "api"
            resource_id = segments[3] if len(segments) > 3 else None
            await _persist(
                db,
                user.get("sub"),
                f"{request.method} {path}",
                resource_type,
                resource_id,
                {"status": response.status_code, "path": path},
                _client_ip(request),
            )
    except Exception:  # noqa: BLE001
        logger.warning("Audit middleware error on %s %s", request.method, request.url.path)
    return response