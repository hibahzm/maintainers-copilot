from fastapi import APIRouter

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
async def create_chat_response() -> dict[str, str]:
    return {"status": "todo", "feature": "streaming chat"}
