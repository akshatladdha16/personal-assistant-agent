"""Utilities for translating between internal resource models and Notion payloads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional


TITLE_PROPERTY = "Title"
URL_PROPERTY = "URL"
NOTES_PROPERTY = "Notes"
TAGS_PROPERTY = "Tags"
CATEGORIES_PROPERTY = "Categories"


@dataclass(slots=True)
class ResourceRecord:
    """Plain representation of a resource stored in Notion."""

    id: str
    title: str
    url: Optional[str]
    notes: Optional[str]
    tags: List[str]
    categories: List[str]
    created_time: datetime


def build_title_property(title: str) -> dict:
    return {"title": [{"text": {"content": title}}]}


def build_rich_text_property(text: str) -> dict:
    return {"rich_text": [{"text": {"content": text}}]}


def build_multi_select_property(values: Iterable[str]) -> dict:
    return {"multi_select": [{"name": value} for value in values if value]}


def parse_page_to_record(page: dict) -> ResourceRecord:
    properties = page.get("properties", {})

    def _extract_title() -> str:
        title_prop = properties.get(TITLE_PROPERTY, {})
        title_items = title_prop.get("title", [])
        if not title_items:
            return "Untitled"
        return title_items[0].get("plain_text") or title_items[0].get("text", {}).get(
            "content", "Untitled"
        )

    def _extract_rich_text(prop_name: str) -> Optional[str]:
        prop = properties.get(prop_name)
        if not prop:
            return None
        text_items = prop.get("rich_text", [])
        return (
            "".join(
                item.get("plain_text") or item.get("text", {}).get("content", "")
                for item in text_items
            )
            or None
        )

    def _extract_multi_select(prop_name: str) -> List[str]:
        prop = properties.get(prop_name, {})
        return [
            item.get("name", "")
            for item in prop.get("multi_select", [])
            if item.get("name")
        ]

    def _extract_url() -> Optional[str]:
        prop = properties.get(URL_PROPERTY, {})
        return prop.get("url")

    created_time = datetime.fromisoformat(page["created_time"].replace("Z", "+00:00"))

    return ResourceRecord(
        id=page["id"],
        title=_extract_title(),
        url=_extract_url(),
        notes=_extract_rich_text(NOTES_PROPERTY),
        tags=_extract_multi_select(TAGS_PROPERTY),
        categories=_extract_multi_select(CATEGORIES_PROPERTY),
        created_time=created_time,
    )
