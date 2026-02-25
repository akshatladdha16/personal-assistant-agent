from __future__ import annotations

import argparse
import sys
from typing import Any, Dict, List, cast

from pathlib import Path

from supabase import Client

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.tools.supabase_client import (  # type: ignore  # noqa: E402
    SupabaseResourceClient,
    _compose_embedding_text,  # type: ignore[attr-defined]
    _generate_embedding,  # type: ignore[attr-defined]
)


def backfill_embeddings(*, batch_size: int) -> int:
    client = SupabaseResourceClient()
    table = client._table  # pylint: disable=protected-access
    raw_client: Client = client._client  # pylint: disable=protected-access

    updated = 0

    while True:
        response = (
            raw_client.table(table)
            .select("id,title,url,notes")
            .is_("embeddings_vector", "null")
            .limit(batch_size)
            .execute()
        )
        rows = cast(List[Dict[str, Any]], response.data or [])
        if not rows:
            break

        for row in rows:
            embed_text = _compose_embedding_text(
                title=row.get("title", ""),
                notes=row.get("notes"),
                url=row.get("url"),
            )
            if not embed_text:
                continue

            vector = _generate_embedding(embed_text)
            if vector is None:
                continue

            raw_client.table(table).update({"embeddings_vector": vector}).eq(
                "id", row.get("id")
            ).execute()
            updated += 1

    return updated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Populate missing vector embeddings for resources"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of rows to fetch per iteration",
    )
    args = parser.parse_args()

    total = backfill_embeddings(batch_size=args.batch_size)
    print(f"Updated embeddings for {total} resources")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:  # pragma: no cover - graceful exit
        sys.exit(1)
