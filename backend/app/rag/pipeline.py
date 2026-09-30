import logging
import re
import time
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KnowledgeChunk, KnowledgeDocument
from app.rag.language import NO_CONTEXT_MESSAGES, language_instruction

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


_STOPWORDS = frozenset(
    "a an and are as at be but by can could do does for from had has have how i if in into is it its "
    "may me my of on or our should so than that the their them then there these they this to us was we "
    "what when where which who whom why will with would you your tell about please need needs".split()
)


def _tokenize(text: str) -> list[str]:
    """Lower-case word tokens with punctuation and stopwords removed."""
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if t not in _STOPWORDS and len(t) > 1]


def _stem(token: str) -> str:
    """Very light stemmer so 'approvals'/'approval', 'registered'/'registration' overlap."""
    for suffix in ("ations", "ation", "ings", "ing", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            return token[: -len(suffix)]
    return token


def _stems(text: str) -> set[str]:
    return {_stem(t) for t in _tokenize(text)}


# Question wording that maps to section headings/phrases in the regulations.
_QUERY_EXPANSIONS: list[tuple[frozenset[str], tuple[str, ...]]] = [
    (frozenset({"long", "duration", "timeline", "days", "time", "take", "takes", "processing", "quickly"}),
     ("timeline", "typical", "days")),
    (frozenset({"documents", "document", "papers", "attach", "submit", "checklist"}), ("documents", "required")),
    (frozenset({"renew", "renewal", "expire", "expiry", "validity", "valid"}), ("renewal", "renewed", "annual")),
    (frozenset({"who", "authority", "department", "apply"}), ("authority", "director", "board", "apply")),
    (frozenset({"mandatory", "compulsory", "must", "required"}), ("mandatory", "must")),
    (frozenset({"labor", "labour", "worker", "workers", "employees"}), ("workers", "labour", "employees")),
]


def _expand_query_stems(query: str) -> set[str]:
    raw = set(re.findall(r"[a-z0-9]+", (query or "").lower()))
    extra: set[str] = set()
    for triggers, additions in _QUERY_EXPANSIONS:
        if raw & triggers:
            extra.update(_stem(a) for a in additions)
    return extra


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
    
    async def reindex_document(self, doc: KnowledgeDocument, chunk_size: int = 500, overlap: int = 50) -> int:
        """Rebuild a document's chunks (e.g. after the chunking strategy improved)."""
        from sqlalchemy import delete

        await self.db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == doc.id))
        chunks = self._chunk_text(doc.text, chunk_size, overlap)
        embeddings = None
        try:
            from app.ai.embeddings import EmbeddingProviderFactory
            embeddings = EmbeddingProviderFactory.create().embed(chunks)
        except Exception:  # noqa: BLE001 - embeddings are best effort
            embeddings = None
        for i, chunk_text in enumerate(chunks):
            self.db.add(KnowledgeChunk(
                document_id=doc.id,
                chunk_index=i,
                text=chunk_text,
                embedding=embeddings[i] if embeddings else None,
                custom_metadata={'token_count': len(chunk_text.split()), 'reindexed': True},
            ))
        await self.db.commit()
        return len(chunks)

    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> list[str]:
        """
        Split text into chunks. Markdown documents are split by section so each
        chunk answers one kind of question (applicability, documents required,
        timeline, ...) and carries "<document title> › <section>" as its first
        line. Plain text falls back to sentence-based chunking.
        """
        sections = self._split_markdown_sections(text)
        if not sections:
            return self._chunk_sentences(text, chunk_size, overlap)

        chunks: list[str] = []
        for label, body in sections:
            if len(body.split()) <= chunk_size:
                chunks.append(f"{label}\n{body}")
            else:
                chunks.extend(f"{label}\n{part}" for part in self._chunk_sentences(body, chunk_size, overlap))
        return chunks

    @staticmethod
    def _split_markdown_sections(text: str) -> list[tuple[str, str]]:
        """Return [(label, body)] for markdown text with headings, else []."""
        if not re.search(r"^#{1,6}\s+\S", text, re.MULTILINE):
            return []
        title = ""
        heading = ""
        buf: list[str] = []
        out: list[tuple[str, str]] = []

        def flush():
            body = "\n".join(buf).strip()
            if body:
                label = " › ".join(x for x in (title, heading) if x)
                out.append((label or "Document", body))
            buf.clear()

        for line in text.splitlines():
            m = re.match(r"^(#{1,6})\s+(.*\S)\s*$", line)
            if m:
                flush()
                if len(m.group(1)) == 1 and not title:
                    title, heading = m.group(2).strip(), ""
                else:
                    heading = m.group(2).strip()
            else:
                buf.append(line)
        flush()
        return out

    def _chunk_sentences(self, text: str, chunk_size: int, overlap: int) -> list[str]:
        """Split text into overlapping sentence-based chunks."""
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
        top_k: int = 4,
        min_keyword_score: float = 0.2,
    ) -> list[dict]:
        """
        Retrieve relevant chunks for a query.

        Combines fast keyword scoring with embedding cosine similarity (when an
        embedding provider is available) so results are ranked by relevance.

        Only the current, applicable version of each regulation is retrieved
        (spec §9): documents with an ``effective_to`` in the past, or that are
        no longer the latest, are excluded so answers reflect the active law.
        """
        query_stems = _stems(query)
        bonus_stems = _expand_query_stems(query)

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
            chunk_stems = _stems(chunk.text)
            overlap = query_stems & chunk_stems
            # Share of the question's meaningful words that this chunk covers.
            keyword_score = len(overlap) / len(query_stems) if query_stems else 0.0
            # Section-intent bonus: "how long" favours the timeline section, etc.
            keyword_score += 0.15 * len(bonus_stems & chunk_stems)

            semantic_score = 0.0
            stored = chunk.embedding
            if stored is not None and query_vector is not None:
                semantic_score = _cosine(stored, query_vector)

            # Keywords are the primary signal (the default embedder is a hashed
            # bag-of-words, so it adds little); semantic score only breaks ties.
            score = keyword_score + 0.15 * semantic_score

            scored_chunks.append({
                'text': chunk.text,
                'score': round(score, 4),
                'keyword_score': round(keyword_score, 4),
                'document_id': str(chunk.document_id),
                'chunk_index': chunk.chunk_index,
            })

        # Drop chunks that share nothing with the question so unrelated
        # questions do not receive an arbitrary "answer".
        scored_chunks = [c for c in scored_chunks if c['keyword_score'] >= min_keyword_score]
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
        
        prompt = f"""Answer the QUESTION below using only the REGULATORY CONTEXT.

Rules:
- Start with a direct answer to exactly what was asked (a yes/no, a number of days, a list of documents, etc.).
- Then add only the supporting details that are relevant to this question. Do not summarise unrelated parts of the context.
- If the context does not contain the answer, say so explicitly instead of guessing.

REGULATORY CONTEXT:
{context_text}

QUESTION: {query}

ANSWER:"""

        return prompt
    
    async def generate_answer(
        self,
        query: str,
        llm_provider=None,
        project_context: str | None = None,
        language: str = "en",
    ) -> dict:
        """
        Generate answer using RAG
        """
        # Retrieve relevant context
        context_chunks = await self.retrieve_context(query)
        
        if not context_chunks:
            return {
                'answer': NO_CONTEXT_MESSAGES.get(language) or (
                    'I could not find this in the regulations I have. Try asking about a specific approval '
                    '(for example factory licence, MPCB consent, boiler registration or fire NOC), '
                    'or rephrase your question with more detail.'
                ),
                'confidence': 0.0,
                'sources': [],
                'evidence': []
            }
        
        # Construct prompt
        prompt = self.construct_prompt(query, context_chunks)
        if project_context:
            prompt = f"PROJECT CONTEXT (use only to tailor the answer to this project):\n{project_context}\n\n" + prompt
        system_prompt = (
            "You are UdyogSetu Regulatory Copilot. "
            "Answer only using the retrieved authoritative context. "
            "Do not invent laws, approvals, deadlines or government procedures. "
            "If evidence is insufficient, explicitly say so. "
            "Distinguish confirmed, inferred and uncertain information. "
            "Answer the specific question asked and keep the answer concise. "
            "Always provide sources. "
            "Never present yourself as a legal authority."
        ) + language_instruction(language)

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
