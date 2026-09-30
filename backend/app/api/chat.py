from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_project_owner
from app.core.database import get_db_session
from app.core.security import get_current_user
from app.schemas import ChatQuery
from app.services.rag_service import RAGService
from app.workflows.copilot_workflow import CopilotWorkflow

router = APIRouter(prefix="/chat", tags=["regulatory-copilot"])

@router.post("/query")
async def query_regulatory_copilot(
    query: ChatQuery,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Route a regulatory/status/document/scheme query to the best engine."""
    if query.project_id:
        await require_project_owner(query.project_id, user, db)
    workflow = CopilotWorkflow(db)
    response = await workflow.route(query.question, query.project_id)
    return response

@router.get("/history/{project_id}")
async def get_chat_history(
    project_id: UUID,
    project: object = Depends(require_project_owner),
    db: AsyncSession = Depends(get_db_session)
):
    """Get chat history for a project"""
    rag_service = RAGService(db)
    history = await rag_service.get_chat_history(project_id)
    return {"messages": history}