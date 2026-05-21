"""PostgreSQL/pgvector and sparse-search queries for RAG chunks."""

import json
import math
from typing import Any

import asyncpg

from app.domain.rag import RetrievedChunk

DEFAULT_DENSE_WEIGHT = 0.25
DEFAULT_CANDIDATE_K = 25


def vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"


class RagRepository:
    def __init__(self, database_url: str, timeout_seconds: float = 10.0) -> None:
        self.database_url = database_url
        self.timeout_seconds = timeout_seconds

    async def search_hybrid(
        self,
        *,
        query_text: str,
        query_embedding: list[float],
        embedding_model: str,
        top_k: int,
        source_type: str | None = None,
        candidate_k: int = DEFAULT_CANDIDATE_K,
        dense_weight: float = DEFAULT_DENSE_WEIGHT,
    ) -> list[RetrievedChunk]:
        dense_candidates = await self.search_dense(
            query_embedding=query_embedding,
            embedding_model=embedding_model,
            top_k=candidate_k,
            source_type=source_type,
        )
        sparse_candidates = await self.search_sparse(
            query_text=query_text,
            top_k=candidate_k,
            source_type=source_type,
        )
        return merge_hybrid_candidates(
            dense_candidates=dense_candidates,
            sparse_candidates=sparse_candidates,
            top_k=top_k,
            dense_weight=dense_weight,
        )

    async def index_stats(self) -> dict[str, Any]:
        sql = """
            SELECT
                COUNT(*)::int AS chunks,
                COUNT(*) FILTER (WHERE embedding IS NOT NULL)::int AS embedded_chunks,
                COUNT(DISTINCT source_id)::int AS sources,
                array_remove(array_agg(DISTINCT embedding_model), NULL) AS embedding_models
            FROM rag_chunks
        """
        rows = await self._fetch(sql)
        if not rows:
            return {"chunks": 0, "embedded_chunks": 0, "sources": 0, "embedding_models": []}
        row = rows[0]
        return {
            "chunks": row["chunks"],
            "embedded_chunks": row["embedded_chunks"],
            "sources": row["sources"],
            "embedding_models": list(row["embedding_models"] or []),
        }

    async def search_dense(
        self,
        *,
        query_embedding: list[float],
        embedding_model: str,
        top_k: int,
        source_type: str | None = None,
    ) -> list[RetrievedChunk]:
        where = "c.embedding IS NOT NULL AND c.embedding_model = $2"
        params: list[Any] = [vector_literal(query_embedding), embedding_model, top_k]
        if source_type is not None:
            where += " AND s.source_type = $4"
            params.append(source_type)

        sql = f"""
            SELECT c.id, c.source_id, c.title, c.parent_title, c.text, s.source_type, c.metadata,
                   1 - (c.embedding <=> $1::vector) AS score
            FROM rag_chunks c
            JOIN rag_sources s ON s.id = c.source_id
            WHERE {where}
            ORDER BY c.embedding <=> $1::vector
            LIMIT $3
        """
        rows = await self._fetch(sql, *params)
        if not rows:
            rows = await self._search_dense_any_model(
                query_embedding=query_embedding,
                top_k=top_k,
                source_type=source_type,
            )
        return [self._row_to_chunk(row, score_field="dense") for row in rows]

    async def _search_dense_any_model(
        self,
        *,
        query_embedding: list[float],
        top_k: int,
        source_type: str | None = None,
    ) -> list[asyncpg.Record]:
        where = "c.embedding IS NOT NULL"
        params: list[Any] = [vector_literal(query_embedding), top_k]
        if source_type is not None:
            where += " AND s.source_type = $3"
            params.append(source_type)

        sql = f"""
            SELECT c.id, c.source_id, c.title, c.parent_title, c.text, s.source_type, c.metadata,
                   1 - (c.embedding <=> $1::vector) AS score
            FROM rag_chunks c
            JOIN rag_sources s ON s.id = c.source_id
            WHERE {where}
            ORDER BY c.embedding <=> $1::vector
            LIMIT $2
        """
        return await self._fetch(sql, *params)

    async def search_sparse(
        self,
        *,
        query_text: str,
        top_k: int,
        source_type: str | None = None,
    ) -> list[RetrievedChunk]:
        where = "c.search_vector @@ websearch_to_tsquery('english', $1)"
        params: list[Any] = [query_text, top_k]
        if source_type is not None:
            where += " AND s.source_type = $3"
            params.append(source_type)

        sql = f"""
            SELECT c.id, c.source_id, c.title, c.parent_title, c.text, s.source_type, c.metadata,
                   ts_rank_cd(c.search_vector, websearch_to_tsquery('english', $1)) AS score
            FROM rag_chunks c
            JOIN rag_sources s ON s.id = c.source_id
            WHERE {where}
            ORDER BY score DESC
            LIMIT $2
        """
        rows = await self._fetch(sql, *params)
        return [self._row_to_chunk(row, score_field="sparse") for row in rows]

    async def _fetch(self, sql: str, *params: Any) -> list[asyncpg.Record]:
        connection = await asyncpg.connect(self.database_url, timeout=self.timeout_seconds)
        try:
            return list(await connection.fetch(sql, *params))
        finally:
            await connection.close()

    def _row_to_chunk(self, row: asyncpg.Record, *, score_field: str) -> RetrievedChunk:
        metadata = row["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        score = float(row["score"])
        return RetrievedChunk(
            chunk_id=row["id"],
            source_id=row["source_id"],
            title=row["title"],
            parent_title=row["parent_title"],
            text=row["text"],
            source_type=row["source_type"],
            score=score,
            dense_score=score if score_field == "dense" else 0.0,
            sparse_score=score if score_field == "sparse" else 0.0,
            metadata=metadata or {},
        )


def merge_hybrid_candidates(
    *,
    dense_candidates: list[RetrievedChunk],
    sparse_candidates: list[RetrievedChunk],
    top_k: int,
    dense_weight: float = DEFAULT_DENSE_WEIGHT,
) -> list[RetrievedChunk]:
    sparse_weight = 1.0 - dense_weight
    dense_by_id = {chunk.chunk_id: chunk for chunk in dense_candidates}
    sparse_by_id = {chunk.chunk_id: chunk for chunk in sparse_candidates}
    dense_norm = _minmax({chunk.chunk_id: chunk.dense_score for chunk in dense_candidates})
    sparse_norm = _minmax({chunk.chunk_id: chunk.sparse_score for chunk in sparse_candidates})

    merged: dict[str, RetrievedChunk] = {}
    for chunk_id in set(dense_by_id) | set(sparse_by_id):
        base = dense_by_id.get(chunk_id) or sparse_by_id[chunk_id]
        dense_score = dense_by_id.get(chunk_id, base).dense_score if chunk_id in dense_by_id else 0.0
        sparse_score = sparse_by_id.get(chunk_id, base).sparse_score if chunk_id in sparse_by_id else 0.0
        score = dense_weight * dense_norm.get(chunk_id, 0.0) + sparse_weight * sparse_norm.get(chunk_id, 0.0)
        merged[chunk_id] = RetrievedChunk(
            chunk_id=base.chunk_id,
            source_id=base.source_id,
            title=base.title,
            parent_title=base.parent_title,
            text=base.text,
            source_type=base.source_type,
            score=score,
            dense_score=dense_score,
            sparse_score=sparse_score,
            metadata=base.metadata,
        )
    return sorted(merged.values(), key=lambda chunk: chunk.score, reverse=True)[:top_k]


def _minmax(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    low = min(scores.values())
    high = max(scores.values())
    if math.isclose(low, high):
        return {key: 1.0 for key in scores}
    return {key: (value - low) / (high - low) for key, value in scores.items()}
