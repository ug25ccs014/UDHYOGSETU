"""Tests for the embedded background task manager."""

import asyncio

import pytest

from app.workers.background import BackgroundTaskManager


@pytest.mark.asyncio
async def test_background_manager_runs_job():
    manager = BackgroundTaskManager(max_workers=2)
    manager.start()

    async def work():
        await asyncio.sleep(0.01)
        return {"done": True}

    job_id = manager.submit(work, name="test_work")
    # Give the worker a moment to pick it up.
    for _ in range(50):
        await asyncio.sleep(0.01)
        job = manager.get_job(job_id)
        if job["status"] == "COMPLETED":
            break
    job = manager.get_job(job_id)
    assert job is not None
    assert job["status"] == "COMPLETED"
    assert job["result"]["done"] is True


@pytest.mark.asyncio
async def test_background_manager_failure_is_captured():
    manager = BackgroundTaskManager(max_workers=1)
    manager.start()

    async def boom():
        raise RuntimeError("boom")

    job_id = manager.submit(boom, name="broken")
    for _ in range(50):
        await asyncio.sleep(0.01)
        job = manager.get_job(job_id)
        if job["status"] in ("COMPLETED", "FAILED"):
            break
    assert job["status"] == "FAILED"
    assert "boom" in job["error"]


def test_background_manager_missing_job_returns_none():
    manager = BackgroundTaskManager()
    assert manager.get_job("nope") is None