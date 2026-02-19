from datetime import datetime, timezone

from src.utils import notion_format as nf


def test_build_multi_select_property_filters_empty_values():
    prop = nf.build_multi_select_property(["ai", "", "agents"])
    assert prop == {"multi_select": [{"name": "ai"}, {"name": "agents"}]}


def test_parse_page_to_record_handles_missing_fields():
    created_time = datetime.now(timezone.utc).isoformat()
    page = {
        "id": "page-123",
        "created_time": created_time,
        "properties": {
            nf.TITLE_PROPERTY: {
                "title": [
                    {
                        "plain_text": "LangGraph Guide",
                    }
                ]
            },
            nf.URL_PROPERTY: {"url": "https://example.com"},
            nf.NOTES_PROPERTY: {
                "rich_text": [
                    {
                        "plain_text": "Looping agents with tools",
                    }
                ]
            },
            nf.TAGS_PROPERTY: {
                "multi_select": [
                    {"name": "ai"},
                    {"name": "langgraph"},
                ]
            },
            nf.CATEGORIES_PROPERTY: {"multi_select": []},
        },
    }

    record = nf.parse_page_to_record(page)

    assert record.id == "page-123"
    assert record.title == "LangGraph Guide"
    assert record.url == "https://example.com"
    assert record.tags == ["ai", "langgraph"]
    assert record.categories == []
    assert record.notes == "Looping agents with tools"
