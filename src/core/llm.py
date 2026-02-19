"""LLM provider factory.

This module centralises language-model construction so the rest of the
codebase can stay agnostic about vendor-specific details. It reads from the
global ``settings`` object and returns a cached ``ChatModel`` instance that
matches the configured provider.
"""

from functools import lru_cache
from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel

from src.core.config import settings


class LLMProviderNotConfigured(RuntimeError):
    """Raised when a selected LLM provider is missing required credentials."""


Provider = Literal["openai", "ollama"]


def _build_openai_llm() -> BaseChatModel:
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:  # pragma: no cover - import error surfaced to user
        raise RuntimeError(
            "langchain-openai is not installed. Install it to use the OpenAI provider."
        ) from exc

    if not settings.openai_api_key:
        raise LLMProviderNotConfigured(
            "OPENAI_API_KEY is required when llm_provider='openai'."
        )

    return ChatOpenAI(
        api_key=settings.openai_api_key.get_secret_value(),
        model="gpt-4o-mini",
        temperature=0.1,
    )


def _build_ollama_llm() -> BaseChatModel:
    try:
        from langchain_ollama import ChatOllama
    except ImportError as exc:  # pragma: no cover - import error surfaced to user
        raise RuntimeError(
            "langchain-ollama is not installed. Install it to use the Ollama provider."
        ) from exc

    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
    )


@lru_cache(maxsize=1)
def get_llm(provider: Provider | None = None) -> BaseChatModel:
    """Return a configured chat model.

    Parameters
    ----------
    provider:
        Optionally override the provider defined in ``settings``. Useful for
        tests where different providers might be exercised without mutating
        global configuration.
    """

    selected_provider: Provider = provider or settings.llm_provider  # type: ignore[assignment]

    if selected_provider == "openai":
        return _build_openai_llm()
    if selected_provider == "ollama":
        return _build_ollama_llm()

    raise RuntimeError(f"Unsupported LLM provider '{selected_provider}'.")
