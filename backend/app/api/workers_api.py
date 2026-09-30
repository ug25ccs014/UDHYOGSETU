"""Background job status API."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_user
from app.workers.background import get_task_manager

router = APIRouter(prefix="/jobs", tags=["background-jobs"])


@router.get("/{job_id}")
async def get_job(job_id: str, user: dict = Depends(get_current_user)):
    job = get_task_manager().get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("")
async def list_jobs(
    user: dict = Depends(get_current_user),
    limit: int = 50,
):
    return {"jobs": get_task_manager().list_jobs(limit)}
