"""Smoke-test dense pgvector retrieval with the selected E5 embedding model."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from typing import Any

from scripts.rag.ingest_pgvector import DEFAULT_DATABASE_URL, DEFAULT_EMBEDDING_MODEL, E5Embedder, vector_literal


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL))
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--source-type", choices=("project_doc", "github_issue"))
    parser.add_argument("--device", default="auto", choices=("auto", "cpu", "cuda"))
    return parser.parse_args()


async def query(args: argparse.Namespace) -> list[dict[str, Any]]:
    try:
        import asyncpg
    except ImportError as exc:  # pragma: no cover - depends on indexing runtime
        raise SystemExit("Missing database dependency. Install it with: pip install asyncpg") from exc

    embedder = E5Embedder(args.embedding_model, device=args.device, batch_size=1)
    vector = embedder.encode([args.question], kind="query")[0]
    where = "embedding IS NOT NULL AND embedding_model = $2"
    params: list[Any] = [vector_literal(vector), args.embedding_model, args.top_k]
    if args.source_type:
        where += " AND source_type = $4"
        params.append(args.source_type)

    sql = f"""
        SELECT id, source_id, title, parent_title, text, source_type, metadata,
               1 - (embedding <=> $1::vector) AS score
        FROM rag_chunks
        WHERE {where}
        ORDER BY embedding <=> $1::vector
        LIMIT $3
    """

    connection = await asyncpg.connect(args.database_url)
    try:
        rows = await connection.fetch(sql, *params)
    finally:
        await connection.close()

    return [
        {
            "chunk_id": row["id"],
            "source_id": row["source_id"],
            "title": row["title"],
            "parent_title": row["parent_title"],
            "source_type": row["source_type"],
            "score": float(row["score"]),
            "metadata": json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"],
            "text_preview": row["text"][:300],
        }
        for row in rows
    ]


def main() -> None:
    args = parse_args()
    print(json.dumps(asyncio.run(query(args)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
