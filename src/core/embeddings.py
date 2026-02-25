from __future__ import annotations

import logging
from functools import lru_cache
from typing import List, Optional

from langchain_openai import OpenAIEmbeddings

try:  # Optional dependency for local embeddings
    from langchain_community.embeddings import OllamaEmbeddings
except ImportError:  # pragma: no cover - optional path
    OllamaEmbeddings = None  # type: ignore[assignment]

from src.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Simple synchronous embedding interface."""

    def embed(self, text: str) -> List[float]:  # pragma: no cover - interface
        raise NotImplementedError


class OpenAIEmbeddingService(EmbeddingService):
    def __init__(self) -> None:
        api_key = (
            settings.openai_api_key.get_secret_value()
            if settings.openai_api_key
            else None
        )
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is required when embedding_provider=openai"
            )
        self._client = OpenAIEmbeddings(
            model=settings.embedding_model,
            openai_api_key=api_key,
        )

    def embed(self, text: str) -> List[float]:
        return self._client.embed_query(text)


class OllamaEmbeddingService(EmbeddingService):
    def __init__(self) -> None:
        if OllamaEmbeddings is None:
            raise RuntimeError(
                "langchain-community is required for embedding_provider=ollama"
            )
        self._client = OllamaEmbeddings(
            base_url=settings.ollama_base_url,
            model=settings.embedding_model,
        )

    def embed(self, text: str) -> List[float]:
        return self._client.embed_query(text)


@lru_cache(maxsize=1)
def get_embedding_service() -> Optional[EmbeddingService]:
    provider = settings.embedding_provider.lower()

    if provider == "none":
        logger.info("Embedding provider disabled; semantic search unavailable")
        return None

    try:
        if provider == "openai":
            return OpenAIEmbeddingService()
        if provider == "ollama":
            return OllamaEmbeddingService()
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to initialise embedding service: %s", exc)
        return None

    logger.error("Unsupported embedding provider: %s", provider)
    return None


def embed_text(text: str) -> Optional[List[float]]:
    if not text.strip():
        return None
    service = get_embedding_service()
    if not service:
        return None
    try:
        return service.embed(text)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("Embedding generation failed: %s", exc)
        return None
