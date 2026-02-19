from src.agent.graph import _coerce_limit, _ensure_list, _normalise_intent


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
