"""Chat orchestration over the project's tools."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.api.schemas.chat import ChatResponse, ChatToolResult
from app.domain.chat import Message
from app.infra.exceptions import ToolFailure
from app.infra.minio import MinioBlobStore
from app.infra.tracing import trace_event
from app.repositories.audit_repo import AuditRepository
from app.services.chat_agent.openai_agent import AgentRunResult, OpenAIChatAgentService
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
        agent_service: OpenAIChatAgentService | None = None,
        conversation_state_service: ConversationStateService | None = None,
        blob_store: MinioBlobStore | None = None,
        conversation_snapshot_bucket: str = "conversation-snapshots",
        conversation_snapshot_retention: int = 25,
        audit_repository: AuditRepository | None = None,
    ) -> None:
        self.rag_service = rag_service
        self.tool_runner = tool_runner
        self.agent_service = agent_service
        self.conversation_state_service = conversation_state_service
        self.blob_store = blob_store
        self.conversation_snapshot_bucket = conversation_snapshot_bucket
        self.conversation_snapshot_retention = conversation_snapshot_retention
        self.audit_repository = audit_repository

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
        tool_policy = tools if tools is not None else ["auto"]
        owner_key = self._conversation_owner_key(user_id)
        response_conversation_id = conversation_id or str(uuid4())
        stored_messages = await self._load_short_term_messages(
            conversation_id,
            owner_key=owner_key,
        )
        conversation_messages = self._merge_short_term_messages(stored_messages, messages)
        latest_user_message = self._latest_user_message(messages)
        trace_event(
            "chat.respond.start",
            conversation_id=response_conversation_id,
            incoming_messages=len(messages),
            stored_messages=len(stored_messages),
            use_rag=use_rag,
            top_k=top_k,
            allow_summarizer=allow_summarizer,
            allow_memory_write=allow_memory_write,
            authenticated=bool(user_id),
        )

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
                owner_key=owner_key,
            )
            trace_event("chat.respond.end", route="empty_prompt")
            return response

        agent_response = await self._run_agent(
            user_id=user_id,
            messages=conversation_messages,
            use_rag=use_rag,
            top_k=top_k,
            allow_summarizer=allow_summarizer,
            allow_memory_write=allow_memory_write,
            tools=tool_policy,
        )
        if agent_response is not None:
            response = ChatResponse(
                conversation_id=response_conversation_id,
                message=Message(role="assistant", content=agent_response.answer),
                citations=agent_response.citations,
                tool_results=agent_response.tool_results,
            )
            await self._save_short_term_messages(
                response_conversation_id,
                conversation_messages,
                response,
                owner_key=owner_key,
            )
            self._snapshot_retrieved_chunks(response_conversation_id, response)
            trace_event(
                "chat.respond.end",
                route="openai_agent",
                tool_results=len(agent_response.tool_results),
                citations=len(agent_response.citations),
            )
            return response

        tool_results = await self._run_chat_tools(
            latest_user_message.content,
            user_id=user_id,
            tools=tool_policy,
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
                owner_key=owner_key,
            )
            self._snapshot_retrieved_chunks(response_conversation_id, response)
            trace_event(
                "chat.respond.end",
                route="deterministic_tools",
                tool_results=[result.name for result in tool_results],
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
                owner_key=owner_key,
            )
            trace_event("chat.respond.end", route="rag_disabled")
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
                owner_key=owner_key,
            )
            trace_event("chat.respond.end", route="rag_failed")
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
            owner_key=owner_key,
        )
        self._snapshot_retrieved_chunks(response_conversation_id, response)
        trace_event("chat.respond.end", route="rag_direct", citations=len(rag_response.citations))
        return response

    async def _run_agent(
        self,
        *,
        user_id: UUID | None,
        messages: list[Message],
        use_rag: bool,
        top_k: int,
        allow_summarizer: bool,
        allow_memory_write: bool,
        tools: list[ChatToolName],
    ) -> AgentRunResult | None:
        if self.agent_service is None or not self.agent_service.is_configured:
            return None
        try:
            return await self.agent_service.respond(
                user_id=user_id,
                messages=[message.model_dump(mode="json") for message in messages],
                use_rag=use_rag,
                top_k=top_k,
                allow_summarizer=allow_summarizer,
                allow_memory_write=allow_memory_write,
                tools=tools,
            )
        except ToolFailure:
            return None

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

    async def _load_short_term_messages(
        self,
        conversation_id: str | None,
        *,
        owner_key: str,
    ) -> list[Message]:
        if conversation_id is None or self.conversation_state_service is None:
            return []
        try:
            return await self.conversation_state_service.load_messages(
                conversation_id,
                owner_key=owner_key,
            )
        except ToolFailure:
            return []

    async def _save_short_term_messages(
        self,
        conversation_id: str,
        conversation_messages: list[Message],
        response: ChatResponse,
        *,
        owner_key: str,
    ) -> None:
        if self.conversation_state_service is None:
            return
        messages_to_save = [*conversation_messages, response.message]
        try:
            await self.conversation_state_service.save_messages(
                conversation_id,
                messages_to_save,
                owner_key=owner_key,
            )
        except ToolFailure:
            return

    async def delete_conversation(self, *, actor_user_id: UUID, conversation_id: str) -> None:
        if self.conversation_state_service is None:
            raise ToolFailure("Short-term conversation memory is unavailable.")
        await self.conversation_state_service.delete_conversation(
            conversation_id,
            owner_key=self._conversation_owner_key(actor_user_id),
        )
        if self.audit_repository is not None:
            await self.audit_repository.record(
                actor_user_id=actor_user_id,
                action="conversation.delete",
                target_type="conversation",
                target_id=conversation_id,
                metadata={"source": "chat_api"},
            )
        trace_event("conversation.deleted", conversation_id=conversation_id)

    def _snapshot_retrieved_chunks(self, conversation_id: str, response: ChatResponse) -> None:
        if self.blob_store is None:
            return
        chunks = [
            chunk.model_dump(mode="json")
            for result in response.tool_results
            for chunk in result.chunks
        ]
        if not chunks:
            return
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        prefix = f"conversation_id={conversation_id}/"
        object_name = f"{prefix}{timestamp}.json"
        payload = {
            "conversation_id": conversation_id,
            "created_at": datetime.now(UTC).isoformat(),
            "citations": response.citations,
            "chunks": chunks,
        }
        try:
            uri = self.blob_store.put_json(
                bucket=self.conversation_snapshot_bucket,
                object_name=object_name,
                payload=payload,
            )
            self.blob_store.prune_prefix(
                bucket=self.conversation_snapshot_bucket,
                prefix=prefix,
                keep=self.conversation_snapshot_retention,
            )
            trace_event("conversation.snapshot.saved", uri=uri, chunks=len(chunks))
        except ToolFailure as exc:
            trace_event("conversation.snapshot.failed", error=str(exc))

    def _merge_short_term_messages(
        self,
        stored_messages: list[Message],
        incoming_messages: list[Message],
    ) -> list[Message]:
        if len(incoming_messages) > 1 or not stored_messages:
            return incoming_messages
        return [*stored_messages, *incoming_messages]

    def _conversation_owner_key(self, user_id: UUID | None) -> str:
        if user_id is None:
            return "anonymous"
        return f"user:{user_id}"
