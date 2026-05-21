from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import ChatServiceDep, CurrentUserDep, OptionalCurrentUserDep
from app.api.schemas.chat import ChatRequest, ChatResponse
from app.api.streaming import chat_sse_events

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


@router.post("/stream")
async def stream_chat_response(
    payload: ChatRequest,
    service: ChatServiceDep,
    current_user: OptionalCurrentUserDep,
) -> StreamingResponse:
    return StreamingResponse(
        chat_sse_events(
            payload=payload,
            service=service,
            user_id=current_user.id if current_user else None,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    service: ChatServiceDep,
    current_user: CurrentUserDep,
) -> None:
    await service.delete_conversation(
        actor_user_id=current_user.id,
        conversation_id=conversation_id,
    )
