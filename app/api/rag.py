from fastapi import APIRouter

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/query")
async def query_rag() -> dict[str, str]:
    return {"status": "todo", "feature": "rag query"}
