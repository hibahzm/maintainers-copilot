"""Chat orchestration over the project's tools."""

from uuid import uuid4

from app.api.schemas.chat import ChatResponse, ChatToolResult
from app.domain.chat import Message
from app.infra.exceptions import ToolFailure
from app.services.rag_service import RagService


class ChatService:
    """Coordinate chat turns and tool calls.

    The first real tool is RAG. Classifier/NER/summarizer can be added as
    explicit tools after the chat UI contract is stable.
    """

    def __init__(self, *, rag_service: RagService) -> None:
        self.rag_service = rag_service

    async def respond(
        self,
        *,
        messages: list[Message],
        conversation_id: str | None,
        use_rag: bool = True,
        top_k: int = 5,
    ) -> ChatResponse:
        latest_user_message = self._latest_user_message(messages)
        response_conversation_id = conversation_id or str(uuid4())
        if latest_user_message is None:
            return ChatResponse(
                conversation_id=response_conversation_id,
                message=Message(
                    role="assistant",
                    content="Send me a maintainer question or issue context to start.",
                ),
            )

        if not use_rag:
            return ChatResponse(
                conversation_id=response_conversation_id,
                message=Message(
                    role="assistant",
                    content="RAG is disabled for this turn, so I cannot ground the answer in project context.",
                ),
            )

        try:
            rag_response = await self.rag_service.query(
                question=latest_user_message.content,
                top_k=top_k,
                generate_answer=True,
            )
        except ToolFailure:
            return ChatResponse(
                conversation_id=response_conversation_id,
                message=Message(
                    role="assistant",
                    content="I could not reach the retrieval tools yet. Try again after the RAG services are running.",
                ),
                tool_results=[ChatToolResult(name="rag.query", status="failed")],
            )

        return ChatResponse(
            conversation_id=response_conversation_id,
            message=Message(role="assistant", content=rag_response.answer),
            citations=rag_response.citations,
            tool_results=[
                ChatToolResult(
                    name="rag.query",
                    status="ok",
                    citations=rag_response.citations,
                    chunks=rag_response.chunks,
                    metadata={
                        "retrieval_mode": rag_response.retrieval_mode,
                        "embedding_model": rag_response.embedding_model,
                        "answer_provider": rag_response.answer_provider,
                        "answer_model": rag_response.answer_model,
                    },
                )
            ],
        )

    def _latest_user_message(self, messages: list[Message]) -> Message | None:
        for message in reversed(messages):
            if message.role == "user" and message.content.strip():
                return message
        return None
