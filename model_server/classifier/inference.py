from fastapi import APIRouter

router = APIRouter(tags=["classifier"])


@router.post("/classify")
async def classify() -> dict[str, str]:
    return {"status": "todo", "feature": "model classification"}
