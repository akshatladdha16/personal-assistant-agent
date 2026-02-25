from __future__ import annotations

from src.tools import supabase_client


def test_expand_keywords_adds_singular_forms() -> None:
    expanded = supabase_client._expand_keywords(["startups"], None)  # type: ignore[attr-defined]
    assert "startups" in expanded
    assert "startup" in expanded


def test_expand_keywords_includes_query_and_variants() -> None:
    expanded = supabase_client._expand_keywords([], "Y Combinator")  # type: ignore[attr-defined]
    assert expanded == ["y combinator"]
