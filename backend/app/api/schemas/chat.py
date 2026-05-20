from typing import Literal

from pydantic import Field

from app.api.schemas.common import APIModel
from app.api.schemas.rag import RagRetrievedChunk
from app.domain.chat import Message


class ChatRequest(APIModel):
    conversation_id: str | None = None
    messages: list[Message] = Field(min_length=1)
    use_rag: bool = True
    top_k: int = Field(default=5, ge=1, le=10)
    allow_summarizer: bool = False
    tools: list[Literal["auto", "rag", "classifier", "ner", "summarizer"]] = Field(
        default_factory=lambda: ["auto"],
        description=(
            "Tool policy for this turn. 'auto' routes from the message; summarizer only runs "
            "when allow_summarizer is true because it may call an LLM."
        ),
    )


class ChatToolResult(APIModel):
    name: str
    status: str
    citations: list[str] = Field(default_factory=list)
    chunks: list[RagRetrievedChunk] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class ChatResponse(APIModel):
    conversation_id: str
    message: Message
    citations: list[str] = Field(default_factory=list)
    tool_results: list[ChatToolResult] = Field(default_factory=list)
