"""High-level helpers for working with the Notion resources database."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional

from notion_client import Client

from src.core.config import settings
from src.utils.notion_format import (
    CATEGORIES_PROPERTY,
    NOTES_PROPERTY,
    TAGS_PROPERTY,
    TITLE_PROPERTY,
    URL_PROPERTY,
    ResourceRecord,
    build_multi_select_property,
    build_rich_text_property,
    build_title_property,
    parse_page_to_record,
)


@dataclass(slots=True)
class ResourceInput:
    """Minimal payload collected from the user or agent before storing."""

    title: str
    url: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    categories: Optional[List[str]] = None


class NotionResourceClient:
    """Wrapper around the Notion API for resource storage and retrieval."""

    def __init__(
        self,
        *,
        client: Optional[Client] = None,
        database_id: Optional[str] = None,
    ) -> None:
        if not settings.notion_api_key or not settings.notion_resource_database_id:
            raise RuntimeError(
                "Notion credentials are missing. Ensure NOTION_API_KEY and "
                "NOTION_RESOURCE_DATABASE_ID are set in your environment."
            )

        self._client = client or Client(auth=settings.notion_api_key.get_secret_value())
        self._database_id = database_id or settings.notion_resource_database_id

    # --- Public API -----------------------------------------------------
    def add_resource(self, payload: ResourceInput) -> ResourceRecord:
        """Persist a resource entry in Notion."""

        properties: dict = {
            TITLE_PROPERTY: build_title_property(payload.title),
        }

        if payload.url:
            properties[URL_PROPERTY] = {"url": payload.url}
        if payload.notes:
            properties[NOTES_PROPERTY] = build_rich_text_property(payload.notes)
        if payload.tags:
            properties[TAGS_PROPERTY] = build_multi_select_property(payload.tags)
        if payload.categories:
            properties[CATEGORIES_PROPERTY] = build_multi_select_property(
                payload.categories
            )

        page = self._client.pages.create(
            parent={"database_id": self._database_id},
            properties=properties,
        )

        return parse_page_to_record(page)

    def fetch_resources(
        self,
        *,
        tags: Optional[Iterable[str]] = None,
        categories: Optional[Iterable[str]] = None,
        query: Optional[str] = None,
        limit: int = 10,
    ) -> List[ResourceRecord]:
        """Retrieve resources using simple tag and keyword filters."""

        filter_payload = self._build_filter(
            tags=tags, categories=categories, query=query
        )

        query_args: dict = {"database_id": self._database_id, "page_size": limit}
        if filter_payload:
            query_args["filter"] = filter_payload

        response = self._client.databases.query(**query_args)
        return [parse_page_to_record(result) for result in response.get("results", [])]

    # --- Internals ------------------------------------------------------
    def _build_filter(
        self,
        *,
        tags: Optional[Iterable[str]] = None,
        categories: Optional[Iterable[str]] = None,
        query: Optional[str] = None,
    ) -> Optional[dict]:
        clauses: List[dict] = []

        if tags:
            tag_filters = [
                {
                    "property": TAGS_PROPERTY,
                    "multi_select": {"contains": tag},
                }
                for tag in tags
                if tag
            ]
            if tag_filters:
                clauses.append({"or": tag_filters})

        if categories:
            category_filters = [
                {
                    "property": CATEGORIES_PROPERTY,
                    "multi_select": {"contains": category},
                }
                for category in categories
                if category
            ]
            if category_filters:
                clauses.append({"or": category_filters})

        if query:
            clauses.append(
                {
                    "property": TITLE_PROPERTY,
                    "title": {"contains": query},
                }
            )

        if not clauses:
            return None

        if len(clauses) == 1:
            return clauses[0]

        return {"and": clauses}
