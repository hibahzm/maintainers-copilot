from fastapi import APIRouter

router = APIRouter(prefix="/classifier", tags=["classifier"])


@router.post("")
async def classify_issue() -> dict[str, str]:
    return {"status": "todo", "feature": "classifier proxy"}
