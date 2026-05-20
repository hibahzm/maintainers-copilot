"""PostgreSQL/pgvector queries for RAG chunks."""

import json
from typing import Any

import asyncpg

from app.domain.rag import RetrievedChunk


def vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"


class RagRepository:
    def __init__(self, database_url: str, timeout_seconds: float = 10.0) -> None:
        self.database_url = database_url
        self.timeout_seconds = timeout_seconds

    async def search_dense(
        self,
        *,
        query_embedding: list[float],
        embedding_model: str,
        top_k: int,
        source_type: str | None = None,
    ) -> list[RetrievedChunk]:
        where = "embedding IS NOT NULL AND embedding_model = $2"
        params: list[Any] = [vector_literal(query_embedding), embedding_model, top_k]
        if source_type is not None:
            where += " AND source_type = $4"
            params.append(source_type)

        sql = f"""
            SELECT id, source_id, title, parent_title, text, source_type, metadata,
                   1 - (embedding <=> $1::vector) AS score
            FROM rag_chunks
            WHERE {where}
            ORDER BY embedding <=> $1::vector
            LIMIT $3
        """
        connection = await asyncpg.connect(self.database_url, timeout=self.timeout_seconds)
        try:
            rows = await connection.fetch(sql, *params)
        finally:
            await connection.close()
        return [self._row_to_chunk(row) for row in rows]

    def _row_to_chunk(self, row: asyncpg.Record) -> RetrievedChunk:
        metadata = row["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        return RetrievedChunk(
            chunk_id=row["id"],
            source_id=row["source_id"],
            title=row["title"],
            parent_title=row["parent_title"],
            text=row["text"],
            source_type=row["source_type"],
            score=float(row["score"]),
            metadata=metadata or {},
        )
