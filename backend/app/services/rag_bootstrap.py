"""Development RAG index bootstrap for fresh local stacks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import asyncpg
import httpx

from app.core.config import Settings
from app.infra.tracing import trace_event
from app.repositories.rag_repo import vector_literal


async def bootstrap_rag_index(settings: Settings) -> None:
    """Load prepared RAG chunks into pgvector when the dev database is empty."""

    if not settings.bootstrap_rag_index:
        return

    chunks_path = Path(settings.rag_bootstrap_chunks_path)
    if not chunks_path.exists():
        trace_event("rag.bootstrap.skipped", reason="chunks_file_missing", path=str(chunks_path))
        return

    conn = await asyncpg.connect(settings.database_url)
    try:
        chunks = _load_chunks(chunks_path)
        if not chunks:
            trace_event("rag.bootstrap.skipped", reason="chunks_file_empty", path=str(chunks_path))
            return

        existing = await conn.fetchval(
            "SELECT COUNT(*) FROM rag_chunks WHERE embedding IS NOT NULL"
        )
        if int(existing or 0) >= len(chunks):
            trace_event("rag.bootstrap.skipped", reason="index_already_present", chunks=existing)
            return

        vectors, embedding_model = await _embed_chunks(
            chunks,
            model_server_url=settings.model_server_url,
            batch_size=max(1, settings.rag_bootstrap_batch_size),
            timeout_seconds=settings.rag_bootstrap_timeout_seconds,
        )
        await _upsert_chunks(conn, chunks=chunks, vectors=vectors, embedding_model=embedding_model)
        trace_event(
            "rag.bootstrap.ready",
            chunks=len(chunks),
            sources=len(_source_rows(chunks)),
            embedding_model=embedding_model,
        )
    finally:
        await conn.close()


def _load_chunks(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


async def _embed_chunks(
    chunks: list[dict[str, Any]],
    *,
    model_server_url: str,
    batch_size: int,
    timeout_seconds: float,
) -> tuple[list[list[float]], str]:
    vectors: list[list[float]] = []
    embedding_model = ""
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            response = await client.post(
                f"{model_server_url.rstrip('/')}/embed",
                json={
                    "texts": [str(chunk.get("text") or "") for chunk in batch],
                    "input_type": "passage",
                },
            )
            response.raise_for_status()
            payload = response.json()
            batch_vectors = payload.get("embeddings") or []
            if len(batch_vectors) != len(batch):
                raise RuntimeError("Model server returned an invalid RAG bootstrap embedding batch.")
            vectors.extend(batch_vectors)
            embedding_model = str(payload.get("model_name") or embedding_model)
            trace_event(
                "rag.bootstrap.embedded_batch",
                embedded=len(vectors),
                total=len(chunks),
                embedding_model=embedding_model,
            )
    if not embedding_model:
        raise RuntimeError("Model server did not return an embedding model name.")
    return vectors, embedding_model


async def _upsert_chunks(
    conn: asyncpg.Connection,
    *,
    chunks: list[dict[str, Any]],
    vectors: list[list[float]],
    embedding_model: str,
) -> None:
    async with conn.transaction():
        await conn.executemany(
            """
            INSERT INTO rag_sources (id, source_type, source_path, title, metadata)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            ON CONFLICT (id) DO UPDATE SET
                source_type = EXCLUDED.source_type,
                source_path = EXCLUDED.source_path,
                title = EXCLUDED.title,
                metadata = EXCLUDED.metadata
            """,
            [
                (
                    source["id"],
                    source["source_type"],
                    source["source_path"],
                    source["title"],
                    json.dumps(source["metadata"], sort_keys=True),
                )
                for source in _source_rows(chunks)
            ],
        )
        await conn.executemany(
            """
            INSERT INTO rag_chunks (
                id, source_id, parent_id, chunk_strategy, title, parent_title, text,
                metadata, start_char, end_char, start_word, end_word,
                embedding, embedding_model
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10, $11, $12, $13::vector, $14)
            ON CONFLICT (id) DO UPDATE SET
                source_id = EXCLUDED.source_id,
                parent_id = EXCLUDED.parent_id,
                chunk_strategy = EXCLUDED.chunk_strategy,
                title = EXCLUDED.title,
                parent_title = EXCLUDED.parent_title,
                text = EXCLUDED.text,
                metadata = EXCLUDED.metadata,
                start_char = EXCLUDED.start_char,
                end_char = EXCLUDED.end_char,
                start_word = EXCLUDED.start_word,
                end_word = EXCLUDED.end_word,
                embedding = EXCLUDED.embedding,
                embedding_model = EXCLUDED.embedding_model
            """,
            [
                (
                    chunk["chunk_id"],
                    chunk["source_id"],
                    chunk.get("parent_id"),
                    chunk.get("chunk_strategy") or "parent_child_sections",
                    chunk.get("title"),
                    chunk.get("parent_title"),
                    chunk.get("text") or "",
                    json.dumps(chunk.get("metadata") or {}, sort_keys=True),
                    chunk.get("start_char"),
                    chunk.get("end_char"),
                    chunk.get("start_word"),
                    chunk.get("end_word"),
                    vector_literal(vector),
                    embedding_model,
                )
                for chunk, vector in zip(chunks, vectors, strict=True)
            ],
        )


def _source_rows(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources: dict[str, dict[str, Any]] = {}
    for chunk in chunks:
        source_id = str(chunk["source_id"])
        if source_id in sources:
            continue
        sources[source_id] = {
            "id": source_id,
            "source_type": chunk.get("source_type") or "unknown",
            "source_path": chunk.get("source_path"),
            "title": chunk.get("title"),
            "metadata": chunk.get("metadata") or {},
        }
    return list(sources.values())
