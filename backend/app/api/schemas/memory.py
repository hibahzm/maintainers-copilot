from app.api.schemas.common import APIModel


class MemoryRecordResponse(APIModel):
    id: str
    content: str


class MemoryListResponse(APIModel):
    items: list[MemoryRecordResponse]
