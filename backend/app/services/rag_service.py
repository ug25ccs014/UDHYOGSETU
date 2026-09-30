from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.pipeline import RAGPipeline


class RAGService:
    """RAG (Retrieval-Augmented Generation) service for regulatory knowledge"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def answer_regulatory_question(self, question: str, project_id: UUID | None = None) -> dict:
        """Answer regulatory question using RAG"""
        pipeline = RAGPipeline(self.db)
        result = await pipeline.generate_answer(question)

        relevant_regulations = [
            source.get("title", "") for source in result["sources"] if source.get("title")
        ]

        return {
            "answer": result["answer"],
            "sources": result["sources"],
            "confidence": result["confidence"],
            "relevant_regulations": relevant_regulations,
        }

    async def get_chat_history(self, project_id: UUID) -> list[dict]:
        """Get chat history for a project"""
        return []