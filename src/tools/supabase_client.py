"""Supabase-backed persistence layer for resources."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, List, Optional, cast

from supabase import Client, create_client

from src.core.config import settings
from src.utils.resource_models import (
    ResourceInput,
    ResourceRecord,
    normalise_string_list,
    row_to_record,
)


class SupabaseResourceClient:
    """Wrapper around Supabase for storing and retrieving resources."""

    def __init__(
        self,
        *,
        client: Optional[Client] = None,
        table_name: Optional[str] = None,
    ) -> None:
        self._client = client or create_client(
            settings.supabase_url,
            settings.supabase_key.get_secret_value(),
        )
        self._table = table_name or settings.supabase_resources_table

    def _find_existing_row(self, payload: ResourceInput) -> Optional[dict[str, Any]]:
        if payload.url:
            response = (
                self._client.table(self._table)
                .select("*")
                .eq("url", payload.url)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = cast(List[Any], response.data or [])
            if rows:
                row = rows[0]
                if isinstance(row, dict):
                    return cast(dict[str, Any], row)

        if payload.title:
            response = (
                self._client.table(self._table)
                .select("*")
                .eq("title", payload.title)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = cast(List[Any], response.data or [])
            if rows:
                row = rows[0]
                if isinstance(row, dict):
                    return cast(dict[str, Any], row)

        return None

    # --- Persistence --------------------------------------------------
    def add_resource(self, payload: ResourceInput) -> ResourceRecord:
        normalised_tags = normalise_string_list(payload.tags)
        normalised_categories = normalise_string_list(payload.categories)

        existing_row = self._find_existing_row(payload)

        update_fields: dict[str, Any] = {}
        if payload.url:
            update_fields["url"] = payload.url
        if payload.notes:
            update_fields["notes"] = payload.notes
        if normalised_tags:
            update_fields["tags"] = normalised_tags[0]
        if normalised_categories:
            update_fields["categories"] = normalised_categories[0]

        if existing_row:
            if not update_fields:
                return row_to_record(existing_row)

            update_builder = (
                self._client.table(self._table)
                .update(update_fields)
                .eq("id", existing_row["id"])
            )
            update_any = cast(Any, update_builder)
            update_response = update_any.select("*").single().execute()
            updated = cast(dict[str, Any], update_response.data or existing_row)
            return row_to_record(updated)

        record_dict = {
            "title": payload.title,
            "url": payload.url,
            "notes": payload.notes,
            "tags": normalised_tags[0] if normalised_tags else None,
            "categories": normalised_categories[0] if normalised_categories else None,
        }

        insert_response = self._client.table(self._table).insert(record_dict).execute()

        inserted_rows = cast(List[Any], insert_response.data or [])
        if inserted_rows:
            first_row = inserted_rows[0]
            if isinstance(first_row, dict):
                return row_to_record(cast(dict[str, Any], first_row))

        # Fallback: fetch the most recent row matching title/url combo
        query_builder = self._client.table(self._table).select("*").limit(1)
        if payload.url:
            query_builder = query_builder.eq("url", payload.url)
        else:
            query_builder = query_builder.eq("title", payload.title)

        query_response = query_builder.order("created_at", desc=True).execute()
        rows = cast(List[Any], query_response.data or [])
        if rows:
            row = rows[0]
            if isinstance(row, dict):
                return row_to_record(cast(dict[str, Any], row))

        # As a last resort, return a record constructed from the payload
        return ResourceRecord(
            id=None,
            title=payload.title,
            url=payload.url,
            notes=payload.notes,
            tags=normalised_tags,
            categories=normalised_categories,
            created_at=datetime.now(),
        )

    def fetch_resources(
        self,
        *,
        tags: Optional[Iterable[str]] = None,
        categories: Optional[Iterable[str]] = None,
        query: Optional[str] = None,
        keywords: Optional[Iterable[str]] = None,
        limit: int = 10,
    ) -> List[ResourceRecord]:
        builder = self._client.table(self._table).select("*")

        tag_values = normalise_string_list(tags)
        if tag_values:
            builder = builder.ilike("tags", f"%{tag_values[0]}%")

        category_values = normalise_string_list(categories)
        if category_values:
            builder = builder.ilike("categories", f"%{category_values[0]}%")

        keyword_list = [kw.strip() for kw in keywords or [] if kw and kw.strip()]

        if not keyword_list and query:
            keyword_list = [query]

        if keyword_list:
            clauses = []
            for kw in keyword_list:
                pattern = f"%{kw}%"
                clauses.append(f"title.ilike.{pattern}")
                clauses.append(f"notes.ilike.{pattern}")
            builder = builder.or_(",".join(clauses))

        response = builder.limit(limit).order("created_at", desc=True).execute()
        rows_json = cast(List[Any], response.data or [])

        records: List[ResourceRecord] = []
        for row in rows_json:
            if isinstance(row, dict):
                records.append(row_to_record(cast(dict[str, Any], row)))

        return records
