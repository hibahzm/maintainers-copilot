from fastapi import APIRouter

router = APIRouter(tags=["summarizer"])


@router.post("/summarize")
async def summarize() -> dict[str, str]:
    return {"status": "todo", "feature": "summarization"}
