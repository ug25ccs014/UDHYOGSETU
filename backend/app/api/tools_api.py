"""API surface for the controlled copilot tools (spec §11).

Exposes:
  * GET  /api/tools            -> list the allow-listed tools (schemas)
  * POST /api/tools/execute    -> execute a validated tool call (scoped to the
                                  authenticated user's own project)

Execution does not accept arbitrary code — only the registered tools run, and
all tools are read-only against the authenticated user's own data.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.tools import ToolCallingError, ToolCallingService
from app.core.database import get_db_session
from app.core.security import get_current_user
from app.models import Project
from app.services.copilot_tools import get_copilot_tools

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("")
async def list_tools(user: dict = Depends(get_current_user)):
    registry = get_copilot_tools()
    return {"tools": registry.list()}


@router.post("/execute")
async def execute_tool(
    body: dict,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    tool_name = body.get("tool")
    args = body.get("args") or {}
    if not tool_name:
        raise HTTPException(status_code=400, detail="Missing 'tool'")

    # Enforce ownership: if a project_id is supplied, it must belong to the user.
    project_id = args.get("project_id")
    if project_id:
        try:
            pid = UUID(str(project_id))
        except (ValueError, AttributeError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid project_id")
        result = await db.execute(select(Project).where(Project.id == pid))
        project = result.scalar_one_or_none()
        if not project or str(project.user_id) != str(user["sub"]):
            raise HTTPException(status_code=403, detail="Not authorized for this project")

    registry = get_copilot_tools()
    service = ToolCallingService(registry, db)
    try:
        outcome = await service.execute(tool_name, args)
    except ToolCallingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return outcome
