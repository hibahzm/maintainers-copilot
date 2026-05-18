from pydantic import Field

from app.api.schemas.common import APIModel
from app.domain.chat import Message


class ChatRequest(APIModel):
    conversation_id: str | None = None
    messages: list[Message] = Field(min_length=1)
