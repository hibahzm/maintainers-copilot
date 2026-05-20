from pydantic import Field

from app.api.schemas.common import APIModel
from app.api.schemas.rag import RagRetrievedChunk
from app.domain.chat import Message


class ChatRequest(APIModel):
    conversation_id: str | None = None
    messages: list[Message] = Field(min_length=1)
    use_rag: bool = True
    top_k: int = Field(default=5, ge=1, le=10)


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
