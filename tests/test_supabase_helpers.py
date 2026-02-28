from __future__ import annotations

from src.tools import supabase_client


def test_expand_keywords_adds_singular_forms() -> None:
    expanded = supabase_client._expand_keywords(["startups"], None)  # type: ignore[attr-defined]
    assert "startups" in expanded
    assert "startup" in expanded


def test_expand_keywords_includes_query_and_variants() -> None:
    expanded = supabase_client._expand_keywords([], "Y Combinator")  # type: ignore[attr-defined]
    assert expanded == ["y combinator"]


def test_summarise_semantic_error_handles_ssl_message() -> None:
    error = Exception("code 525 - SSL handshake failed between Cloudflare and host")
    summary = supabase_client._summarise_semantic_error(error)  # type: ignore[attr-defined]
    assert "SSL handshake" in summary
    assert "keyword matches" in summary


def test_summarise_semantic_error_falls_back_to_reason() -> None:
    error = Exception("rate limit exceeded")
    summary = supabase_client._summarise_semantic_error(error)  # type: ignore[attr-defined]
    assert "rate limit exceeded" in summary
