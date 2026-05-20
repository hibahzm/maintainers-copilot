"""Long-term memory persistence queries."""

from datetime import datetime
from uuid import UUID, uuid4

import asyncpg
from pydantic import BaseModel


class MemoryRecord(BaseModel):
    id: str
    user_id: str
    memory_type: str
    content: str
    created_at: datetime
    updated_at: datetime


class MemoryRepository:
    """Persist explicit user memories and their audit events."""

    def __init__(self, *, database_url: str) -> None:
        self.database_url = database_url

    async def create_memory(
        self,
        *,
        user_id: UUID,
        memory_type: str,
        content: str,
        embedding: list[float] | None,
    ) -> MemoryRecord:
        memory_id = uuid4()
        vector_literal = self._vector_literal(embedding) if embedding is not None else None
        conn = await asyncpg.connect(self.database_url)
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO memory (id, user_id, memory_type, content, embedding)
                VALUES ($1, $2, $3, $4, $5::vector)
                RETURNING
                    id::text,
                    user_id::text,
                    memory_type,
                    content,
                    created_at,
                    updated_at
                """,
                memory_id,
                user_id,
                memory_type,
                content,
                vector_literal,
            )
            await conn.execute(
                """
                INSERT INTO audit_log (id, actor_user_id, action, target_type, target_id, metadata)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                """,
                uuid4(),
                user_id,
                "memory.write",
                "memory",
                str(memory_id),
                '{"source":"explicit_write_memory_tool"}',
            )
        finally:
            await conn.close()

        if row is None:
            raise RuntimeError("Memory insert did not return a row.")
        return MemoryRecord.model_validate(dict(row))

    async def list_memories(self, *, user_id: UUID, limit: int = 50) -> list[MemoryRecord]:
        conn = await asyncpg.connect(self.database_url)
        try:
            rows = await conn.fetch(
                """
                SELECT
                    id::text,
                    user_id::text,
                    memory_type,
                    content,
                    created_at,
                    updated_at
                FROM memory
                WHERE user_id = $1
                ORDER BY updated_at DESC, created_at DESC
                LIMIT $2
                """,
                user_id,
                limit,
            )
        finally:
            await conn.close()
        return [MemoryRecord.model_validate(dict(row)) for row in rows]

    def _vector_literal(self, embedding: list[float]) -> str:
        return "[" + ",".join(str(float(value)) for value in embedding) + "]"
