from src.agent.graph import (
    _coerce_limit,
    _ensure_list,
    _extract_keywords,
    _normalise_intent,
)


def test_ensure_list_handles_strings_and_iterables():
    assert _ensure_list("ai, agents , langgraph") == ["ai", "agents", "langgraph"]
    assert _ensure_list(["dev", " ", "ml"]) == ["dev", "ml"]
    assert _ensure_list(None) == []


def test_coerce_limit_bounds_values():
    assert _coerce_limit(3) == 3
    assert _coerce_limit(100) == 25
    assert _coerce_limit("7") == 7
    assert _coerce_limit("not-a-number") == 5


def test_normalise_intent_maps_aliases():
    assert _normalise_intent("Store") == "store_resource"
    assert _normalise_intent("FETCH") == "fetch_resource"
    assert _normalise_intent("chat") == "chat"
    assert _normalise_intent(None) == "chat"
    assert _normalise_intent("recommend") == "fetch_resource"


def test_extract_keywords_filters_stopwords_and_duplicates():
    text = "can you fetch me anything related to chatGPT tools please"
    assert _extract_keywords(text) == ["chatgpt", "tools"]
    assert _extract_keywords("hello") == ["hello"]
    assert _extract_keywords(None) == []
