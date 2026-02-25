from __future__ import annotations

from typing import List, Optional

import pytest

from src.tools import supabase_client


def test_compose_embedding_text_combines_fields() -> None:
    text = supabase_client._compose_embedding_text(  # type: ignore[attr-defined]
        title="Great Article",
        notes="Deep dive into embeddings",
        url="https://example.com",
    )
    assert "Great Article" in text
    assert "Deep dive" in text
    assert "https://example.com" in text


@pytest.mark.parametrize(
    "vector, expected",
    [([0.1, 0.2], [0.1, 0.2]), ([0.0, 0.0], [0.0, 0.0])],
)
def test_generate_embedding_accepts_matching_dimensions(
    monkeypatch: pytest.MonkeyPatch,
    vector: List[float],
    expected: List[float],
) -> None:
    monkeypatch.setattr(supabase_client, "embed_text", lambda _: vector)

    original = supabase_client.settings.embedding_dimensions
    supabase_client.settings.embedding_dimensions = len(vector)
    try:
        result = supabase_client._generate_embedding("hello")  # type: ignore[attr-defined]
        assert result == expected
    finally:
        supabase_client.settings.embedding_dimensions = original


def test_generate_embedding_rejects_dimension_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(supabase_client, "embed_text", lambda _: [0.1, 0.2, 0.3])

    original = supabase_client.settings.embedding_dimensions
    supabase_client.settings.embedding_dimensions = 2
    try:
        result = supabase_client._generate_embedding("hello")  # type: ignore[attr-defined]
        assert result is None
    finally:
        supabase_client.settings.embedding_dimensions = original


def test_generate_embedding_handles_provider_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_embed(_: str) -> Optional[List[float]]:
        return None

    monkeypatch.setattr(supabase_client, "embed_text", fake_embed)
    original = supabase_client.settings.embedding_dimensions
    supabase_client.settings.embedding_dimensions = 2
    try:
        assert supabase_client._generate_embedding("hello") is None  # type: ignore[attr-defined]
    finally:
        supabase_client.settings.embedding_dimensions = original
