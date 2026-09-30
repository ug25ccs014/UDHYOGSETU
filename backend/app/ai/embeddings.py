"""Embedding provider abstraction.

Production UDYOGSETU stores chunk embeddings in PostgreSQL via pgvector. This
module abstracts where embeddings come from so the RAG pipeline does not depend
on a single vendor. Development defaults to a local, dependency-light
``MockEmbeddingProvider`` (deterministic hashed vectors) so the whole RAG flow
works on machines with no ML stack; a Sentence-Transformers provider can be
activated simply by installing ``sentence-transformers``.
"""

from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.core.config import settings

logger = logging.getLogger(__name__)

try:  # optional dependency
    from sentence_transformers import SentenceTransformer  # type: ignore
    _ST_AVAILABLE = True
except ImportError:  # pragma: no cover
    _ST_AVAILABLE = False


class EmbeddingProvider(ABC):
    """Interface implemented by concrete embedding providers."""

    name: str = "base"
    dimension: int = 384

    @abstractmethod
    def embed(self, texts: Sequence[str], normalize: bool = True) -> list[list[float]]:
        """Embed a batch of texts into vectors."""

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic hashed bag-of-words vectors.

    Provides a real (if simplistic) vector so retrieval ranking works end to
    end without any external ML dependency. Good enough for the SIH prototype
    and for tests; swap in a real provider for semantic quality production.
    """

    name = "mock"
    dimension = 128

    def _token_vector(self, token: str) -> list[float]:
        vec = [0.0] * self.dimension
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        # Deterministically place the token's energy into a few buckets.
        for byte in digest:
            idx = byte % self.dimension
            vec[idx] += 1.0
        return vec

    def embed(self, texts: Sequence[str], normalize: bool = True) -> list[list[float]]:
        vectors = []
        for text in texts:
            tokens = text.lower().split()
            if not tokens:
                vec = [0.0] * self.dimension
                vectors.append(vec)
                continue
            vec = [0.0] * self.dimension
            for token in tokens:
                tv = self._token_vector(token)
                for i in range(self.dimension):
                    vec[i] += tv[i]
            if normalize:
                norm = (sum(x * x for x in vec) ** 0.5) or 1.0
                vec = [x / norm for x in vec]
            vectors.append(vec)
        return vectors


class SentenceTransformersEmbeddingProvider(EmbeddingProvider):
    """Wraps the ``sentence-transformers`` library for real semantic vectors."""

    name = "sentence-transformers"

    def __init__(self, model_name: str | None = None):
        if not _ST_AVAILABLE:
            raise RuntimeError("sentence-transformers is not installed.")
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self._model = SentenceTransformer(self.model_name)
        self.dimension = self._model.get_sentence_embedding_dimension()

    def is_available(self) -> bool:
        return _ST_AVAILABLE

    def embed(self, texts: Sequence[str], normalize: bool = True) -> list[list[float]]:
        return self._model.encode(list(texts), normalize_embeddings=normalize).tolist()


class EmbeddingProviderFactory:
    """Builds the configured embedding provider with graceful fallback."""

    @classmethod
    def create(cls, name: str | None = None) -> EmbeddingProvider:
        name = (name or settings.EMBEDDING_PROVIDER or "mock").lower()
        if name in ("sentence-transformers", "st", "sbert"):
            try:
                return SentenceTransformersEmbeddingProvider()
            except Exception as exc:  # noqa: BLE001 - model load can fail on download/OS state
                logger.warning("Falling back to mock embeddings: %s", exc)
                return MockEmbeddingProvider()
        return MockEmbeddingProvider()