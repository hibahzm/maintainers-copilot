"""Chat orchestration over the project's tools."""

from uuid import UUID, uuid4

from app.api.schemas.chat import ChatResponse, ChatToolResult
from app.domain.chat import Message
from app.infra.exceptions import ToolFailure
from app.services.chat_tools.renderer import render_tool_answer
from app.services.chat_tools.runner import ChatToolRunner
from app.services.chat_tools.types import ChatToolName
from app.services.conversation_state_service import ConversationStateService
from app.services.rag_service import RagService


class ChatService:
    """Coordinate chat turns and tool calls.

    RAG answers general project questions. Classifier and NER are cheap local
    model-server tools. Summarization is LLM-backed, so it only runs when the
    caller explicitly enables it for the turn.
    """

    def __init__(
        self,
        *,
        rag_service: RagService,
        tool_runner: ChatToolRunner | None = None,
        conversation_state_service: ConversationStateService | None = None,
    ) -> None:
        self.rag_service = rag_service
        self.tool_runner = tool_runner
        self.conversation_state_service = conversation_state_service

    async def respond(
        self,
        *,
        user_id: UUID | None = None,
        messages: list[Message],
        conversation_id: str | None,
        use_rag: bool = True,
        top_k: int = 5,
        allow_summarizer: bool = False,
        allow_memory_write: bool = False,
        tools: list[ChatToolName] | None = None,
    ) -> ChatResponse:
        response_conversation_id = conversation_id or str(uuid4())
        stored_messages = await self._load_short_term_messages(conversation_id)
        conversation_messages = self._merge_short_term_messages(stored_messages, messages)
        latest_user_message = self._latest_user_message(messages)

        if latest_user_message is None:
            response = ChatResponse(
                conversation_id=response_conversation_id,
                message=Message(
                    role="assistant",
                    content="Send me a maintainer question or issue context to start.",
                ),
            )
            await self._save_short_term_messages(
                response_conversation_id,
                conversation_messages,
                response,
            )
            return response

        tool_results = await self._run_chat_tools(
            latest_user_message.content,
            user_id=user_id,
            tools=tools or ["auto"],
            use_rag=use_rag,
            allow_summarizer=allow_summarizer,
            allow_memory_write=allow_memory_write,
        )
        if tool_results:
            response = ChatResponse(
                conversation_id=response_conversation_id,
                message=Message(
                    role="assistant",
                    content=render_tool_answer(tool_results),
                ),
                tool_results=tool_results,
            )
            await self._save_short_term_messages(
                response_conversation_id,
                conversation_messages,
                response,
            )
            return response

        if not use_rag:
            response = ChatResponse(
                conversation_id=response_conversation_id,
                message=Message(
                    role="assistant",
                    content=(
                        "RAG is disabled for this turn, so I cannot ground the answer "
                        "in project context."
                    ),
                ),
            )
            await self._save_short_term_messages(
                response_conversation_id,
                conversation_messages,
                response,
            )
            return response

        try:
            rag_response = await self.rag_service.query(
                question=latest_user_message.content,
                top_k=top_k,
                generate_answer=True,
            )
        except ToolFailure:
            response = ChatResponse(
                conversation_id=response_conversation_id,
                message=Message(
                    role="assistant",
                    content=(
                        "I could not reach the retrieval tools yet. Try again after "
                        "the RAG services are running."
                    ),
                ),
                tool_results=[ChatToolResult(name="rag.query", status="failed")],
            )
            await self._save_short_term_messages(
                response_conversation_id,
                conversation_messages,
                response,
            )
            return response

        response = ChatResponse(
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
        await self._save_short_term_messages(
            response_conversation_id,
            conversation_messages,
            response,
        )
        return response

    async def _run_chat_tools(
        self,
        text: str,
        *,
        user_id: UUID | None,
        tools: list[ChatToolName],
        use_rag: bool,
        allow_summarizer: bool,
        allow_memory_write: bool,
    ) -> list[ChatToolResult]:
        if self.tool_runner is None:
            return []
        return await self.tool_runner.run(
            text,
            user_id=user_id,
            tools=tools,
            use_rag=use_rag,
            allow_summarizer=allow_summarizer,
            allow_memory_write=allow_memory_write,
        )

    def _latest_user_message(self, messages: list[Message]) -> Message | None:
        for message in reversed(messages):
            if message.role == "user" and message.content.strip():
                return message
        return None

    async def _load_short_term_messages(self, conversation_id: str | None) -> list[Message]:
        if conversation_id is None or self.conversation_state_service is None:
            return []
        try:
            return await self.conversation_state_service.load_messages(conversation_id)
        except ToolFailure:
            return []

    async def _save_short_term_messages(
        self,
        conversation_id: str,
        conversation_messages: list[Message],
        response: ChatResponse,
    ) -> None:
        if self.conversation_state_service is None:
            return
        messages_to_save = [*conversation_messages, response.message]
        try:
            await self.conversation_state_service.save_messages(conversation_id, messages_to_save)
        except ToolFailure:
            return

    def _merge_short_term_messages(
        self,
        stored_messages: list[Message],
        incoming_messages: list[Message],
    ) -> list[Message]:
        if len(incoming_messages) > 1 or not stored_messages:
            return incoming_messages
        return [*stored_messages, *incoming_messages]

