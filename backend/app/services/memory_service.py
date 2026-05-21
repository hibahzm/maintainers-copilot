"""Explicit memory writes and memory listing."""

from typing import Any
from uuid import UUID

import httpx

from app.api.schemas.memory import MemoryCreateRequest, MemoryRecordResponse
from app.infra.exceptions import ToolFailure
from app.infra.redaction import redact
from app.repositories.memory_repo import MemoryRecord, MemoryRepository


class MemoryService:
    """Coordinate pgvector-backed memory writes and audit events.

    Memory writes are explicit only. The chatbot should call this service only
    when the user asks to remember something; normal chat turns are not stored
    as long-term memory.
    """

    def __init__(
        self,
        *,
        database_url: str,
        model_server_url: str,
        repository: MemoryRepository | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        self.model_server_url = model_server_url.rstrip("/")
        self.repository = repository or MemoryRepository(database_url=database_url)
        self.timeout_seconds = timeout_seconds

    async def write_memory(
        self,
        *,
        user_id: UUID,
        payload: MemoryCreateRequest,
    ) -> MemoryRecordResponse:
        redacted_content = redact(payload.content)
        embedding = await self._embed_memory(redacted_content)
        record = await self.repository.create_memory(
            user_id=user_id,
            memory_type=payload.memory_type,
            content=redacted_content,
            embedding=embedding,
        )
        return self._record_response(record)

    async def list_memories(self, *, user_id: UUID, limit: int = 50) -> list[MemoryRecordResponse]:
        records = await self.repository.list_memories(user_id=user_id, limit=limit)
        return [self._record_response(record) for record in records]

    async def _embed_memory(self, content: str) -> list[float]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.model_server_url}/embed",
                    json={"texts": [content], "input_type": "passage"},
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ToolFailure("Memory embedding request failed.") from exc

        data: dict[str, Any] = response.json()
        embeddings = data.get("embeddings") or []
        if len(embeddings) != 1:
            raise ToolFailure(
                "Embedding model server returned an invalid memory embedding payload."
            )
        return embeddings[0]

    def _record_response(self, record: MemoryRecord) -> MemoryRecordResponse:
        return MemoryRecordResponse.model_validate(record.model_dump())
