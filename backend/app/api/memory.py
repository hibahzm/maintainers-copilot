from fastapi import APIRouter

from app.api.dependencies import MemoryServiceDep
from app.api.schemas.memory import MemoryListResponse

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("", response_model=MemoryListResponse)
async def list_memories(service: MemoryServiceDep) -> MemoryListResponse:
    _ = service
    return MemoryListResponse(items=[])
