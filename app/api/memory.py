from fastapi import APIRouter

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("")
async def list_memories() -> dict[str, str]:
    return {"status": "todo", "feature": "list memories"}
