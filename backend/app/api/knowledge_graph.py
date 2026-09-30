"""Knowledge graph API (spec §31)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_owned_project
from app.core.database import get_db_session
from app.core.security import get_current_user
from app.services.knowledge_graph import KnowledgeGraphService

router = APIRouter(prefix="/knowledge-graph", tags=["knowledge-graph"])


@router.get("/{project_id}")
async def project_knowledge_graph(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    project=Depends(get_owned_project),
):
    """Build the entity/relationship graph for a project."""
    return await KnowledgeGraphService(db).build_graph(project.id)
