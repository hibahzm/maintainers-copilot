from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.api.schemas.memory import MemoryCreateRequest
from app.repositories.memory_repo import MemoryRecord
from app.services.memory_service import MemoryService


class FakeMemoryRepository:
    def __init__(self):
        self.created = None

    async def create_memory(self, *, user_id, memory_type, content, embedding):
        self.created = {
            "user_id": user_id,
            "memory_type": memory_type,
            "content": content,
            "embedding": embedding,
        }
        now = datetime.now(UTC)
        return MemoryRecord(
            id=str(uuid4()),
            user_id=str(user_id),
            memory_type=memory_type,
            content=content,
            created_at=now,
            updated_at=now,
        )


class FakeMemoryService(MemoryService):
    def __init__(self, *, repository):
        super().__init__(
            database_url="postgresql://unused",
            model_server_url="http://model-server",
            repository=repository,
        )
        self.embedded_content = None

    async def _embed_memory(self, content: str) -> list[float]:
        self.embedded_content = content
        return [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_memory_write_redacts_before_embedding_and_storage():
    repository = FakeMemoryRepository()
    service = FakeMemoryService(repository=repository)
    user_id = uuid4()

    record = await service.write_memory(
        user_id=user_id,
        payload=MemoryCreateRequest(
            content="Remember api_key=sk-test-secret for later.",
            memory_type="semantic",
        ),
    )

    assert "sk-test-secret" not in service.embedded_content
    assert "api_key=[REDACTED]" in service.embedded_content
    assert repository.created["content"] == service.embedded_content
    assert record.content == service.embedded_content
