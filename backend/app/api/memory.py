from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import CurrentUserDep, MemoryServiceDep
from app.api.schemas.memory import MemoryCreateRequest, MemoryListResponse, MemoryRecordResponse
from app.infra.exceptions import ToolFailure

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("", response_model=MemoryListResponse)
async def list_memories(
    current_user: CurrentUserDep,
    service: MemoryServiceDep,
    limit: int = Query(default=50, ge=1, le=100),
) -> MemoryListResponse:
    return MemoryListResponse(items=await service.list_memories(user_id=current_user.id, limit=limit))


@router.post("", response_model=MemoryRecordResponse, status_code=status.HTTP_201_CREATED)
async def write_memory(
    payload: MemoryCreateRequest,
    current_user: CurrentUserDep,
    service: MemoryServiceDep,
) -> MemoryRecordResponse:
    try:
        return await service.write_memory(user_id=current_user.id, payload=payload)
    except ToolFailure as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
