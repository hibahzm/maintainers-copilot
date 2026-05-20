from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.api.schemas.common import APIModel

MemoryType = Literal["semantic", "episodic", "procedural"]


class MemoryCreateRequest(APIModel):
    user_id: UUID
    content: str = Field(min_length=1, max_length=4000)
    memory_type: MemoryType = "semantic"


class MemoryRecordResponse(APIModel):
    id: str
    user_id: str
    memory_type: str
    content: str
    created_at: datetime
    updated_at: datetime


class MemoryListResponse(APIModel):
    items: list[MemoryRecordResponse]
