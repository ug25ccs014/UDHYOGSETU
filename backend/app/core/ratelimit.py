import logging

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as aioredis
except ImportError:  # pragma: no cover
    aioredis = None


class RateLimiter:
    """Redis-backed token bucket limiter with graceful open fallback."""

    def __init__(self, redis_url: str, per_minute: int):
        self.per_minute = max(1, per_minute)
        self._client = None
        self._redis_url = redis_url
        self._enabled = False
        self._attempted = False

    async def _ensure_client(self):
        if self._attempted:
            return
        self._attempted = True
        if aioredis is None:
            return
        try:
            self._client = aioredis.from_url(
                self._redis_url,
                socket_connect_timeout=1,
                retry_on_timeout=False,
            )
            await self._client.ping()
            self._enabled = True
            logger.info("Rate limiter enabled (%s req/min)", self.per_minute)
        except Exception as exc:  # noqa: BLE001 - depends on infra; fail open
            logger.warning("Redis unavailable; rate limiting disabled: %s", exc)
            self._client = None

    async def allow(self, client_key: str) -> bool:
        if not self._enabled:
            return True
        bucket = f"ratelimit:{client_key}"
        try:
            # Fixed-window: increment and expire after 60s.
            current = await self._client.incr(bucket)
            if current == 1:
                await self._client.expire(bucket, 60)
            return current <= self.per_minute
        except Exception as exc:  # noqa: BLE001 - fail open when Redis is flaky
            logger.warning("Rate limit check failed; allowing request: %s", exc)
            return True


rate_limiter = RateLimiter(settings.REDIS_URL, settings.RATE_LIMIT_PER_MINUTE)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        await rate_limiter._ensure_client()

        # Only rate-limit the API routes, not health checks or docs.
        if request.url.path.startswith("/api") and not request.url.path.startswith("/api/health"):
            client_ip = request.client.host if request.client else "unknown"
            if not await rate_limiter.allow(client_ip):
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Too many requests. Please slow down and try again.",
                        "retry_after": 60,
                    },
                    headers={"Retry-After": "60"},
                )
        return await call_next(request)