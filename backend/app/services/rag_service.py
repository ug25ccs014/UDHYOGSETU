from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.pipeline import RAGPipeline


class RAGService:
    """RAG (Retrieval-Augmented Generation) service for regulatory knowledge"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def answer_regulatory_question(self, question: str, project_id: UUID | None = None, language: str = "en") -> dict:
        """Answer regulatory question using RAG"""
        pipeline = RAGPipeline(self.db)
        project_context = await self._project_context(project_id)
        if language and language != "en":
            result = await pipeline.generate_answer(question, project_context=project_context, language=language)
        else:
            result = await pipeline.generate_answer(question, project_context=project_context)

        relevant_regulations = [
            source.get("title", "") for source in result["sources"] if source.get("title")
        ]

        return {
            "answer": result["answer"],
            "sources": result["sources"],
            "confidence": result["confidence"],
            "relevant_regulations": relevant_regulations,
        }

    async def _project_context(self, project_id: UUID | None) -> str | None:
        """Short description of the user's project so answers can be tailored to it."""
        if not project_id:
            return None
        try:
            from app.services.project import ProjectService

            project = await ProjectService(self.db).get_project(project_id)
        except Exception:  # noqa: BLE001 - context is an optional enhancement
            return None
        if not project:
            return None
        fields = ("name", "sector", "project_type", "location", "investment_amount", "employee_count")
        parts = [f"{f}: {getattr(project, f)}" for f in fields if getattr(project, f, None) not in (None, "")]
        return "; ".join(parts) or None

    async def get_chat_history(self, project_id: UUID) -> list[dict]:
        """Get chat history for a project"""
        return []