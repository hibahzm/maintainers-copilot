from fastapi import APIRouter

from app.api.dependencies import ChatServiceDep, OptionalCurrentUserDep
from app.api.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def create_chat_response(
    payload: ChatRequest,
    service: ChatServiceDep,
    current_user: OptionalCurrentUserDep,
) -> ChatResponse:
    return await service.respond(
        user_id=current_user.id if current_user else None,
        messages=payload.messages,
        conversation_id=payload.conversation_id,
        use_rag=payload.use_rag,
        top_k=payload.top_k,
        allow_summarizer=payload.allow_summarizer,
        allow_memory_write=payload.allow_memory_write,
        tools=payload.tools,
    )
