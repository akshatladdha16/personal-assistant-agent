"""Shared resource data models and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, List, Optional


@dataclass(slots=True)
class ResourceRecord:
    """Representation of a stored resource row."""

    id: Any
    title: str
    url: Optional[str]
    notes: Optional[str]
    tags: List[str]
    categories: List[str]
    created_at: datetime


@dataclass(slots=True)
class ResourceInput:
    """Data required to create a resource row."""

    title: str
    url: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    categories: Optional[List[str]] = None


def normalise_string_list(values: Optional[Iterable[str]]) -> List[str]:
    if not values:
        return []
    normalised: List[str] = []
    for value in values:
        text = (value or "").strip()
        if text:
            normalised.append(text)
    return normalised


def row_to_record(row: dict[str, Any]) -> ResourceRecord:
    return ResourceRecord(
        id=row.get("id"),
        title=row.get("title", "Untitled"),
        url=row.get("url"),
        notes=row.get("notes"),
        tags=_coerce_single_to_list(row.get("tags")),
        categories=_coerce_single_to_list(row.get("categories")),
        created_at=_parse_datetime(row.get("created_at")),
    )


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now()


def _coerce_single_to_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []
