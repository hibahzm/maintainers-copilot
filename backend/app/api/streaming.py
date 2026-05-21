"""Server-sent event helpers for chat responses."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from uuid import UUID

from app.api.schemas.chat import ChatRequest
from app.infra.tracing import trace_event
from app.services.chat_service import ChatService


async def chat_sse_events(
    *,
    payload: ChatRequest,
    service: ChatService,
    user_id: UUID | None,
) -> AsyncIterator[str]:
    """Yield a chat response as SSE metadata, tool, delta, final, and done events."""

    try:
        response = await service.respond(
            user_id=user_id,
            messages=payload.messages,
            conversation_id=payload.conversation_id,
            use_rag=payload.use_rag,
            top_k=payload.top_k,
            allow_summarizer=payload.allow_summarizer,
            allow_memory_write=payload.allow_memory_write,
            tools=payload.tools,
        )
    except Exception as exc:
        trace_event("chat.stream.failed", error_type=type(exc).__name__)
        yield sse_event("error", {"message": "Chat request failed. Check the API logs."})
        return

    yield sse_event(
        "metadata",
        {
            "conversation_id": response.conversation_id,
            "citations": response.citations,
        },
    )
    for tool_result in response.tool_results:
        yield sse_event("tool_result", tool_result.model_dump(mode="json"))

    for chunk in _text_chunks(response.message.content):
        yield sse_event("delta", {"content": chunk})
        await asyncio.sleep(0.025)

    yield sse_event("final", response.model_dump(mode="json"))
    yield sse_event("done", {})


def sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


def _text_chunks(text: str, *, size: int = 18) -> list[str]:
    if not text:
        return [""]
    return [text[index : index + size] for index in range(0, len(text), size)]
