"""AI observability logging (spec §34).

Stores non-sensitive metadata about AI/LLM interactions so cost, latency and
reliability can be monitored. Sensitive material (API keys, passwords, complete
documents, auth tokens) is never recorded.
"""

from __future__ import annotations

import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AIEventLog

logger = logging.getLogger(__name__)


class AIObservability:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_event(
        self,
        *,
        request_type: str,
        user_id=None,
        project_id=None,
        model: str | None = None,
        latency_ms: int | None = None,
        token_count: int | None = None,
        success: bool = True,
        error_kind: str | None = None,
        metadata: dict | None = None,
    ) -> AIEventLog:
        """Persist a single AI interaction record (metadata must be non-sensitive)."""
        record = AIEventLog(
            user_id=user_id,
            project_id=project_id,
            request_type=request_type,
            model=model,
            latency_ms=latency_ms,
            token_count=token_count,
            success=success,
            error_kind=error_kind,
            event_metadata=(metadata or {}),
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def summary(self, limit: int = 100) -> dict:
        """Aggregate metrics over recent logged AI interactions."""
        from sqlalchemy import case, func, select

        result = await self.db.execute(
            select(
                func.count(AIEventLog.id),
                func.avg(AIEventLog.latency_ms),
                func.sum(AIEventLog.token_count),
                func.sum(case((AIEventLog.success.is_(True), 1), else_=0)),
            )
        )
        total, avg_latency, total_tokens, successes = result.one()
        total = total or 0
        success_count = successes or 0
        return {
            "total_calls": total,
            "successful_calls": int(success_count),
            "failed_calls": int(total - success_count),
            "avg_latency_ms": round(avg_latency, 1) if avg_latency else None,
            "total_tokens": int(total_tokens) if total_tokens else 0,
        }


class timed_ai_event:
    """Context manager helper that records latency around a call.

    Usage:
        async with timed_ai_event(obs, request_type="generation", ...):
            result = await call()
    """

    def __init__(self, obs: AIObservability, request_type: str, **meta):
        self.obs = obs
        self.request_type = request_type
        self.meta = meta
        self._exception = None

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not hasattr(self, "_logged"):
            self._logged = True
            latency = int((time.perf_counter() - self._start) * 1000)
            success = exc_type is None
            # Fire-and-forget: do not raise on logging failure.
            try:
                import asyncio

                async def _write():
                    await self.obs.log_event(
                        request_type=self.request_type,
                        latency_ms=latency,
                        success=success,
                        error_kind=exc_val.__class__.__name__ if exc_val else None,
                        **{k: v for k, v in self.meta.items() if k in (
                            "user_id", "project_id", "model", "token_count", "metadata",
                        )},
                    )

                asyncio.create_task(_write())
            except Exception as exc:  # noqa: BLE001 - telemetry must never raise
                logger.debug("Fire-and-forget observability task could not be scheduled: %s", exc)
        return False  # propagate the original exception
