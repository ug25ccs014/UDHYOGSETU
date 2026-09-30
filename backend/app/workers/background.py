"""Lightweight in-process background task runner.

While production could swap in Celery/RQ, this embedded asyncio queue keeps the
OCR/embedding/RAG-ingest workloads off the request path without adding infra.
Jobs are tracked in-memory with a status; the job status endpoints let the
frontend poll for completion.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class BackgroundTaskManager:
    """Run async jobs in the background and report their status."""

    def __init__(self, max_workers: int = 4):
        self._jobs: dict[str, dict[str, Any]] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._max_workers = max_workers
        self._started = False

    def start(self):
        if self._started:
            return
        self._started = True
        for _ in range(self._max_workers):
            asyncio.create_task(self._worker())

    async def _worker(self):
        while True:
            job_id, fn = await self._queue.get()
            job = self._jobs.get(job_id)
            if job:
                job["status"] = JobStatus.RUNNING
                job["started_at"] = iso_now()
            try:
                result = await fn()
                if job:
                    job["status"] = JobStatus.COMPLETED
                    job["result"] = result
                    job["completed_at"] = iso_now()
            except Exception as exc:
                logger.exception("Background job %s failed", job_id)
                if job:
                    job["status"] = JobStatus.FAILED
                    job["error"] = str(exc)
                    job["completed_at"] = iso_now()
            finally:
                self._queue.task_done()

    def submit(self, fn: Callable[[], Awaitable[Any]], name: str = "") -> str:
        job_id = str(uuid.uuid4())
        job = {
            "id": job_id,
            "name": name or fn.__name__,
            "status": JobStatus.PENDING,
            "created_at": iso_now(),
        }
        self._jobs[job_id] = job
        self._queue.put_nowait((job_id, fn))
        return job_id

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        job = self._jobs.get(job_id)
        if not job:
            return None
        # Collapse the enum value into a plain string for JSON serialization.
        out = dict(job)
        out["status"] = job["status"].value
        return out

    def list_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
        jobs = list(self._jobs.values())[-limit:]
        return [self.get_job(j["id"]) for j in jobs]


def iso_now() -> str:
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"


_task_manager: BackgroundTaskManager | None = None


def get_task_manager() -> BackgroundTaskManager:
    global _task_manager
    if _task_manager is None:
        _task_manager = BackgroundTaskManager()
    return _task_manager