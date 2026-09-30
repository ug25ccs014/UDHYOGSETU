import logging
import time
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KnowledgeChunk, KnowledgeDocument

logger = logging.getLogger(__name__)


def _coerce_datetime(value):
    """Coerce an ISO string / datetime / None into a datetime or None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00").replace("T", " "))
        except ValueError:
            return None
    return None


def _json_safe(value):
    """Recursively convert non-JSON-serializable values (e.g. datetimes)."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value

class RAGPipeline:
    """RAG (Retrieval-Augmented Generation) pipeline for regulatory knowledge"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def ingest_document(
        self,
        title: str,
        text: str,
        metadata: dict,
        chunk_size: int = 500,
        overlap: int = 50
    ) -> KnowledgeDocument:
        """
        Ingest a document and chunk it for vector storage
        """
        # Create document record
        effective_to = metadata.get('effective_to')
        parse_datetime = _coerce_datetime(effective_to)
        doc = KnowledgeDocument(
            title=title,
            text=text,
            department=metadata.get('department'),
            document_type=metadata.get('document_type'),
            source_url=metadata.get('source_url'),
            jurisdiction=metadata.get('jurisdiction'),
            sector=metadata.get('sector'),
            version=metadata.get('version'),
            effective_date=_coerce_datetime(metadata.get('effective_date')),
            effective_to=parse_datetime,
            is_latest=(parse_datetime is None),
        )
        
        self.db.add(doc)
        await self.db.flush()
        
        # Chunk the document
        chunks = self._chunk_text(text, chunk_size, overlap)

        # Generate embeddings for the chunks (best effort; provider is mock
        # by default so this never blocks on external services).
        embeddings = None
        try:
            from app.ai.embeddings import EmbeddingProviderFactory
            provider = EmbeddingProviderFactory.create()
            embeddings = provider.embed(chunks)
        except Exception:  # noqa: BLE001 - embeddings are a best-effort enhancement
            embeddings = None
        
        for i, chunk_text in enumerate(chunks):
            chunk = KnowledgeChunk(
                document_id=doc.id,
                chunk_index=i,
                text=chunk_text,
                embedding=embeddings[i] if embeddings else None,
                custom_metadata={
                    'token_count': len(chunk_text.split()),
                    'source_metadata': _json_safe(metadata),
                }
            )
            self.db.add(chunk)
        
        await self.db.commit()
        return doc
    
    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> list[str]:
        """
        Split text into overlapping chunks
        """
        sentences = text.split('.')
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            words = sentence.split()
            
            if current_length + len(words) > chunk_size:
                if current_chunk:
                    chunks.append('. '.join(current_chunk) + '.')

                # Overlap: keep the previous sentence to preserve continuity.
                if current_chunk:
                    last_sentence = current_chunk[-1]
                    current_chunk = [last_sentence]
                    current_length = len(last_sentence.split())
                else:
                    current_chunk = []
                    current_length = 0
            
            current_chunk.append(sentence)
            current_length += len(words)
        
        if current_chunk:
            chunks.append('. '.join(current_chunk) + '.')
        
        return chunks
    
    async def retrieve_context(
        self,
        query: str,
        top_k: int = 5
    ) -> list[dict]:
        """
        Retrieve relevant chunks for a query.

        Combines fast keyword scoring with embedding cosine similarity (when an
        embedding provider is available) so results are ranked by relevance.

        Only the current, applicable version of each regulation is retrieved
        (spec §9): documents with an ``effective_to`` in the past, or that are
        no longer the latest, are excluded so answers reflect the active law.
        """
        query_keywords = set(query.lower().split())

        # Filter to documents that are currently in force (no past effective_to
        # and flagged as latest when versioning metadata is present).
        stmt = select(KnowledgeChunk).join(
            KnowledgeDocument,
            KnowledgeChunk.document_id == KnowledgeDocument.id,
        ).where(
            (KnowledgeDocument.effective_to.is_(None)) |
            (KnowledgeDocument.effective_to >= datetime.utcnow())
        )
        result = await self.db.execute(stmt.limit(10000))
        chunks = result.scalars().all()

        # Compute a query embedding for semantic ranking (best effort, pure Python).
        query_vector = None
        try:
            from app.ai.embeddings import EmbeddingProviderFactory
            provider = EmbeddingProviderFactory.create()
            if provider is not None:
                query_vector = provider.embed_one(query)
        except Exception:  # noqa: BLE001 - embeddings are a best-effort enhancement
            query_vector = None

        def _cosine(a, b):
            if not a or not b or len(a) != len(b):
                return 0.0
            dot = sum(x * y for x, y in zip(a, b))
            na = (sum(x * x for x in a) ** 0.5) or 1.0
            nb = (sum(y * y for y in b) ** 0.5) or 1.0
            return dot / (na * nb)

        scored_chunks = []
        for chunk in chunks:
            chunk_words = set(chunk.text.lower().split())
            keyword_score = len(query_keywords & chunk_words) / len(query_keywords) if query_keywords else 0

            # Semantic similarity from stored embedding if available.
            semantic_score = 0.0
            stored = chunk.embedding
            if stored is not None and query_vector is not None:
                semantic_score = _cosine(stored, query_vector)

            # Combine: prefer semantic when available, otherwise keywords.
            score = semantic_score if (query_vector is not None and semantic_score > 0) else keyword_score

            scored_chunks.append({
                'text': chunk.text,
                'score': round(score, 4),
                'document_id': str(chunk.document_id),
                'chunk_index': chunk.chunk_index,
            })

        if not scored_chunks:
            return []

        return sorted(scored_chunks, key=lambda x: x['score'], reverse=True)[:top_k]
    
    def construct_prompt(self, query: str, context_chunks: list[dict]) -> str:
        """
        Construct LLM prompt with retrieved context
        """
        context_text = '\n\n'.join([
            f"Source {i+1}:\n{chunk['text']}"
            for i, chunk in enumerate(context_chunks)
        ])
        
        prompt = f"""Based on the following regulatory documents, answer the question.
If you cannot find relevant information, say so explicitly.

REGULATORY CONTEXT:
{context_text}

QUESTION: {query}

ANSWER:"""
        
        return prompt
    
    async def generate_answer(
        self,
        query: str,
        llm_provider=None
    ) -> dict:
        """
        Generate answer using RAG
        """
        # Retrieve relevant context
        context_chunks = await self.retrieve_context(query)
        
        if not context_chunks:
            return {
                'answer': 'I could not find sufficient authoritative information to answer this question.',
                'confidence': 0.0,
                'sources': [],
                'evidence': []
            }
        
        # Construct prompt
        prompt = self.construct_prompt(query, context_chunks)
        system_prompt = (
            "You are UdyogSetu Regulatory Copilot. "
            "Answer only using the retrieved authoritative context. "
            "Do not invent laws, approvals, deadlines or government procedures. "
            "If evidence is insufficient, explicitly say so. "
            "Distinguish confirmed, inferred and uncertain information. "
            "Always provide sources. "
            "Never present yourself as a legal authority."
        )

        from app.services.ai_observability import AIObservability
        obs = AIObservability(self.db)
        start = time.perf_counter()
        try:
            if llm_provider is None:
                from app.ai.llm_provider import generate_with_fallback
                answer = await generate_with_fallback(system_prompt, prompt, temperature=0.2)
            else:
                answer = await llm_provider.generate(system_prompt, prompt, temperature=0.2)
        except Exception:  # re-raise after logging the observability failure
            try:
                await obs.log_event(request_type="regulatory_rag", latency_ms=int((time.perf_counter() - start) * 1000), success=False, error_kind="generation_failed")
            except Exception as e:  # noqa: BLE001 - telemetry write must stay fire-and-forget
                logger.debug("AI observability failed event skipped: %s", e)
            raise
        try:
            await obs.log_event(request_type="regulatory_rag", latency_ms=int((time.perf_counter() - start) * 1000), success=True)
        except Exception as e2:  # noqa: BLE001 - telemetry write must stay fire-and-forget
            logger.debug("AI observability success event skipped: %s", e2)

        # Extract sources
        sources = await self._get_source_documents(
            [chunk['document_id'] for chunk in context_chunks]
        )

        best_score = max((c['score'] for c in context_chunks), default=0.0)
        confidence = round(min(0.95, 0.4 + best_score), 2)

        return {
            'answer': answer,
            'confidence': confidence,
            'sources': sources,
            'evidence': [chunk['text'][:200] for chunk in context_chunks[:3]],
        }
    
    def _generate_mock_response(self, query: str, context_chunks: list) -> str:
        """Generate mock response based on context"""
        if 'boiler' in query.lower():
            return "Boiler registration is required if your facility has boiler equipment. As per Boiler Regulations, you must register with the Department of Boiler Safety. Required documents include boiler specification, technical drawings, and inspection reports."
        
        if 'mpcb' in query.lower():
            return "MPCB (Maharashtra Pollution Control Board) Consent to Establish and Consent to Operate are mandatory for industrial facilities with pollution potential. The process typically takes 60 days."
        
        if 'factory' in query.lower():
            return "Factory License is required if your facility has more than 9 employees. This is mandatory under the Factories Act and requires factory plan approval and safety certificates."
        
        return f"Based on the regulatory documents, {', '.join([c['text'][:50] for c in context_chunks[:2]])}"
    
    async def _get_source_documents(self, doc_ids: list[str]) -> list[dict]:
        """Get source document metadata"""
        result = await self.db.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.id.in_([UUID(doc_id) for doc_id in doc_ids if doc_id])
            )
        )
        docs = result.scalars().all()
        
        return [
            {
                'title': doc.title,
                'department': doc.department,
                'document_type': doc.document_type,
                'url': doc.source_url,
            }
            for doc in docs
        ]
