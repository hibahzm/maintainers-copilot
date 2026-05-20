from fastapi import APIRouter

from app.api.dependencies import ChatServiceDep
from app.api.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def create_chat_response(
    payload: ChatRequest,
    service: ChatServiceDep,
) -> ChatResponse:
    return await service.respond(
        messages=payload.messages,
        conversation_id=payload.conversation_id,
        use_rag=payload.use_rag,
        top_k=payload.top_k,
    )
