"""Supabase-backed persistence layer for resources."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Iterable, List, Optional, Tuple, cast

from supabase import Client, create_client

try:  # Optional dependency provided by supabase-py
    from postgrest.exceptions import APIError
except ImportError:  # pragma: no cover - defensive fallback
    APIError = None  # type: ignore[assignment]

from src.core.config import settings
from src.core.embeddings import embed_text
from src.utils.resource_models import (
    ResourceInput,
    ResourceRecord,
    normalise_string_list,
    row_to_record,
)


logger = logging.getLogger(__name__)


def _compose_embedding_text(
    *, title: str, notes: Optional[str], url: Optional[str]
) -> Optional[str]:
    parts = [title.strip()]
    if notes:
        parts.append(notes.strip())
    if url:
        parts.append(url.strip())

    combined = "\n".join(segment for segment in parts if segment)
    return combined or None


def _generate_embedding(text: str) -> Optional[List[float]]:
    vector = embed_text(text)
    if vector is None:
        return None

    expected = settings.embedding_dimensions
    if expected and len(vector) != expected:
        logger.warning(
            "Embedding length %s differs from expected %s; skipping store",
            len(vector),
            expected,
        )
        return None

    return vector


def _summarise_semantic_error(error: Exception) -> str:
    reason = _extract_error_message(error)
    reason_lower = reason.lower()

    if "ssl handshake" in reason_lower or "code 525" in reason_lower:
        return (
            "Semantic search is temporarily unavailable because Supabase reported an "
            "SSL handshake error. Showing keyword matches only."
        )

    if reason:
        return f"Semantic search unavailable ({reason}). Showing keyword matches only."

    return "Semantic search is unavailable right now. Showing keyword matches only."


def _extract_error_message(error: Exception) -> str:
    details: List[str] = []

    if APIError is not None and isinstance(error, APIError):  # pragma: no cover - optional
        for attr in ("message", "code", "hint"):
            value = getattr(error, attr, None)
            if value:
                details.append(str(value))

    raw = " - ".join(details) if details else str(error).strip()
    if not raw:
        raw = error.__class__.__name__

    cleaned = re.sub(r"\s+", " ", raw)
    if len(cleaned) > 200:
        return cleaned[:199] + "…"
    return cleaned


def _expand_keywords(keywords: Iterable[str], query: Optional[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []

    def add(term: Optional[str]) -> None:
        if not term:
            return
        value = term.strip().lower()
        if not value:
            return
        if value in seen:
            return
        seen.add(value)
        ordered.append(value)

    for raw in keywords:
        add(raw)
        lowered = raw.strip().lower()
        if len(lowered) > 3:
            if lowered.endswith("ies"):
                add(lowered[:-3] + "y")
            if lowered.endswith("es"):
                add(lowered[:-2])
            if lowered.endswith("s"):
                add(lowered[:-1])
        if "-" in lowered:
            add(lowered.replace("-", " "))

    add(query)
    return ordered


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

        embedding_vector: Optional[List[float]] = None
        embedding_text = _compose_embedding_text(
            title=payload.title,
            notes=payload.notes,
            url=payload.url,
        )

        if existing_row:
            current_text = _compose_embedding_text(
                title=str(existing_row.get("title", "")),
                notes=existing_row.get("notes"),
                url=existing_row.get("url"),
            )
            if current_text == embedding_text:
                embedding_text = None

        if embedding_text:
            embedding_vector = _generate_embedding(embedding_text)

        update_fields: dict[str, Any] = {}
        if payload.url:
            update_fields["url"] = payload.url
        if payload.notes:
            update_fields["notes"] = payload.notes
        if normalised_tags:
            update_fields["tags"] = normalised_tags[0]
        if normalised_categories:
            update_fields["categories"] = normalised_categories[0]
        if embedding_vector is not None:
            update_fields["embeddings_vector"] = embedding_vector

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
        if embedding_vector is not None:
            record_dict["embeddings_vector"] = embedding_vector

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
    ) -> Tuple[List[ResourceRecord], List[str]]:
        tag_values = normalise_string_list(tags)
        category_values = normalise_string_list(categories)

        combined: dict[Any, ResourceRecord] = {}
        notices: List[str] = []

        if query:
            try:
                semantic_results = self._semantic_search(
                    query=query,
                    tags=tag_values,
                    categories=category_values,
                    limit=limit,
                )
                for record in semantic_results:
                    combined[record.id] = record
                    if len(combined) >= limit:
                        return list(combined.values()), notices
            except Exception as exc:  # pragma: no cover - defensive guard
                warning = _summarise_semantic_error(exc)
                notices.append(warning)
                logger.warning(
                    "Semantic search failed for query '%s': %s",
                    query,
                    warning,
                )
                logger.debug("Semantic search stack trace", exc_info=True)

        keyword_results = self._keyword_search(
            tags=tag_values,
            categories=category_values,
            query=query,
            keywords=keywords,
            limit=limit * 2,
        )

        for record in keyword_results:
            if record.id not in combined:
                combined[record.id] = record
            if len(combined) >= limit:
                break

        return list(combined.values()), notices

    def _keyword_search(
        self,
        *,
        tags: List[str],
        categories: List[str],
        query: Optional[str],
        keywords: Optional[Iterable[str]],
        limit: int,
    ) -> List[ResourceRecord]:
        builder = self._client.table(self._table).select("*")

        if tags:
            builder = builder.ilike("tags", f"%{tags[0]}%")

        if categories:
            builder = builder.ilike("categories", f"%{categories[0]}%")

        base_keywords = [kw.strip() for kw in keywords or [] if kw and kw.strip()]
        expanded_keywords = _expand_keywords(base_keywords, query)

        if expanded_keywords:
            clauses = []
            for kw in expanded_keywords:
                pattern = f"%{kw}%"
                clauses.append(f"title.ilike.{pattern}")
                clauses.append(f"notes.ilike.{pattern}")
                clauses.append(f"url.ilike.{pattern}")
                clauses.append(f"tags.ilike.{pattern}")
                clauses.append(f"categories.ilike.{pattern}")
            builder = builder.or_(",".join(clauses))

        response = builder.limit(limit).order("created_at", desc=True).execute()
        rows_json = cast(List[Any], response.data or [])

        records: List[ResourceRecord] = []
        for row in rows_json:
            if isinstance(row, dict):
                records.append(row_to_record(cast(dict[str, Any], row)))

        return records

    def _semantic_search(
        self,
        *,
        query: str,
        tags: List[str],
        categories: List[str],
        limit: int,
    ) -> List[ResourceRecord]:
        embedding = _generate_embedding(query)
        if embedding is None:
            return []

        params: dict[str, Any] = {
            "query_embedding": embedding,
            "match_count": limit,
            "match_threshold": settings.embedding_match_threshold,
        }
        if tags:
            params["filter_tags"] = tags
        if categories:
            params["filter_categories"] = categories

        response = self._client.rpc("match_resources", params).execute()
        rows_json = cast(List[Any], response.data or [])

        records: List[ResourceRecord] = []
        for row in rows_json:
            if isinstance(row, dict):
                records.append(row_to_record(cast(dict[str, Any], row)))

        return records
