from datetime import datetime, timezone

from src.utils.resource_models import normalise_string_list, row_to_record


def test_normalise_string_list_trims_and_drops_empty():
    assert normalise_string_list([" ai ", "", "agents"]) == ["ai", "agents"]
    assert normalise_string_list(None) == []


def test_row_to_record_parses_datetime_strings():
    created_at = datetime.now(timezone.utc).isoformat()
    row = {
        "id": "123",
        "title": "LangGraph Guide",
        "url": "https://example.com",
        "notes": "looping",
        "tags": ["ai"],
        "categories": ["agents"],
        "created_at": created_at,
    }

    record = row_to_record(row)

    assert record.id == "123"
    assert record.title == "LangGraph Guide"
    assert record.url == "https://example.com"
    assert record.tags == ["ai"]
    assert record.categories == ["agents"]
    assert record.created_at.isoformat().startswith(created_at[:19])
