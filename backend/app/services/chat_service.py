"""Chat orchestration over the project's tools."""

from typing import Literal
from uuid import UUID, uuid4

from app.api.schemas.chat import ChatResponse, ChatToolResult
from app.api.schemas.memory import MemoryCreateRequest
from app.domain.chat import Message
from app.infra.exceptions import ToolFailure
from app.services.conversation_state_service import ConversationStateService
from app.services.maintainer_tools_service import MaintainerToolsService
from app.services.memory_service import MemoryService
from app.services.rag_service import RagService

ChatToolName = Literal["auto", "rag", "classifier", "ner", "summarizer", "write_memory"]


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
        tools_service: MaintainerToolsService | None = None,
        memory_service: MemoryService | None = None,
        conversation_state_service: ConversationStateService | None = None,
    ) -> None:
        self.rag_service = rag_service
        self.tools_service = tools_service
        self.memory_service = memory_service
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

        selected_tools = self._select_tools(
            latest_user_message.content,
            tools=tools or ["auto"],
            use_rag=use_rag,
            allow_summarizer=allow_summarizer,
            allow_memory_write=allow_memory_write,
        )
        memory_result = await self._run_memory_tool(
            latest_user_message.content,
            user_id=user_id,
            selected_tools=selected_tools,
            allow_memory_write=allow_memory_write,
        )
        if memory_result is not None:
            response = ChatResponse(
                conversation_id=response_conversation_id,
                message=Message(
                    role="assistant",
                    content=self._render_tool_answer([memory_result]),
                ),
                tool_results=[memory_result],
            )
            await self._save_short_term_messages(
                response_conversation_id,
                conversation_messages,
                response,
            )
            return response

        tool_results = await self._run_issue_tools(
            latest_user_message.content,
            selected_tools=selected_tools,
            allow_summarizer=allow_summarizer,
        )
        if tool_results:
            response = ChatResponse(
                conversation_id=response_conversation_id,
                message=Message(
                    role="assistant",
                    content=self._render_tool_answer(tool_results),
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

    async def _run_issue_tools(
        self,
        text: str,
        *,
        selected_tools: set[str],
        allow_summarizer: bool,
    ) -> list[ChatToolResult]:
        if self.tools_service is None:
            return []

        title, body = self._split_issue_text(text)
        results: list[ChatToolResult] = []

        if "classifier" in selected_tools:
            try:
                classification = await self.tools_service.classify_issue(title=title, body=body)
                results.append(
                    ChatToolResult(
                        name="classifier.classify",
                        status="ok",
                        metadata=classification.model_dump(mode="json"),
                    )
                )
            except ToolFailure as exc:
                results.append(
                    ChatToolResult(
                        name="classifier.classify",
                        status="failed",
                        metadata={"error": str(exc)},
                    )
                )

        if "ner" in selected_tools:
            try:
                entities = await self.tools_service.extract_entities(
                    title=title,
                    body=body,
                    text=text,
                )
                results.append(ChatToolResult(name="ner.extract", status="ok", metadata=entities))
            except ToolFailure as exc:
                results.append(
                    ChatToolResult(
                        name="ner.extract",
                        status="failed",
                        metadata={"error": str(exc)},
                    )
                )

        if "summarizer" in selected_tools and allow_summarizer:
            try:
                summary = await self.tools_service.summarize_issue(
                    title=title,
                    body=body,
                    text=text,
                )
                results.append(
                    ChatToolResult(name="summarizer.summarize", status="ok", metadata=summary)
                )
            except ToolFailure as exc:
                results.append(
                    ChatToolResult(
                        name="summarizer.summarize",
                        status="failed",
                        metadata={"error": str(exc)},
                    )
                )

        return results

    async def _run_memory_tool(
        self,
        text: str,
        *,
        user_id: UUID | None,
        selected_tools: set[str],
        allow_memory_write: bool,
    ) -> ChatToolResult | None:
        if "write_memory" not in selected_tools:
            return None
        if not allow_memory_write:
            return ChatToolResult(
                name="memory.write",
                status="blocked",
                metadata={"error": "Memory writes require allow_memory_write=true."},
            )
        if user_id is None:
            return ChatToolResult(
                name="memory.write",
                status="blocked",
                metadata={"error": "Memory writes require a user_id until auth is wired in."},
            )
        if self.memory_service is None:
            return ChatToolResult(
                name="memory.write",
                status="failed",
                metadata={"error": "Memory service is unavailable."},
            )

        content = self._memory_content(text)
        try:
            record = await self.memory_service.write_memory(
                MemoryCreateRequest(user_id=user_id, content=content, memory_type="semantic")
            )
            return ChatToolResult(
                name="memory.write",
                status="ok",
                metadata=record.model_dump(mode="json"),
            )
        except (ToolFailure, RuntimeError) as exc:
            return ChatToolResult(
                name="memory.write",
                status="failed",
                metadata={"error": str(exc)},
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

    def _select_tools(
        self,
        text: str,
        *,
        tools: list[ChatToolName],
        use_rag: bool,
        allow_summarizer: bool,
        allow_memory_write: bool,
    ) -> set[str]:
        explicit = {tool for tool in tools if tool != "auto"}
        if explicit:
            return {tool for tool in explicit if tool != "rag"}

        lowered = text.lower()
        selected: set[str] = set()
        if any(word in lowered for word in ("classify", "classification", "label", "triage")):
            selected.add("classifier")
        if any(word in lowered for word in ("ner", "entity", "entities", "extract")):
            selected.add("ner")
        summary_keywords = ("summarize", "summary", "tl;dr", "tldr")
        if allow_summarizer and any(word in lowered for word in summary_keywords):
            selected.add("summarizer")
        if allow_memory_write and any(
            phrase in lowered for phrase in ("remember", "save this memory", "write memory")
        ):
            selected.add("write_memory")

        if selected:
            return selected
        return set() if use_rag else selected

    def _split_issue_text(self, text: str) -> tuple[str, str]:
        cleaned_lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
        if not cleaned_lines:
            return "Untitled issue", ""

        title = cleaned_lines[0]
        instruction_prefixes = (
            "classify this issue:",
            "classify:",
            "label this issue:",
            "label:",
            "triage this issue:",
            "extract entities:",
            "summarize this issue:",
            "summarize:",
        )
        lowered_title = title.lower()
        for prefix in instruction_prefixes:
            if lowered_title.startswith(prefix):
                title = title[len(prefix) :].strip() or "Untitled issue"
                break

        body = "\n".join(cleaned_lines[1:])
        return title[:300], body

    def _memory_content(self, text: str) -> str:
        lowered = text.lower()
        for prefix in ("remember that", "remember:", "save this memory:", "write memory:"):
            if lowered.startswith(prefix):
                return text[len(prefix) :].strip()
        return text.strip()

    def _render_tool_answer(self, tool_results: list[ChatToolResult]) -> str:
        lines = ["Here is the tool output for this issue:"]
        for result in tool_results:
            if result.name == "memory.write":
                if result.status == "ok":
                    lines.append("- Memory saved explicitly.")
                else:
                    error = result.metadata.get("error", "memory write failed")
                    lines.append(f"- Memory was not saved: {error}")
                continue

            if result.status != "ok":
                lines.append(f"- {result.name}: unavailable right now.")
                continue

            if result.name == "classifier.classify":
                label = result.metadata.get("label", "unknown")
                confidence = result.metadata.get("confidence", 0.0)
                lines.append(f"- Classification: **{label}** ({confidence:.1%} confidence).")
            elif result.name == "ner.extract":
                grouped = result.metadata.get("grouped", {})
                if grouped:
                    compact = "; ".join(
                        f"{kind}: {', '.join(values[:5])}"
                        for kind, values in grouped.items()
                        if values
                    )
                    lines.append(f"- Extracted entities: {compact}.")
                else:
                    lines.append("- Extracted entities: none found.")
            elif result.name == "summarizer.summarize":
                summary = result.metadata.get("summary", "")
                risk = result.metadata.get("risk_level", "unknown")
                lines.append(f"- Summary: {summary}")
                lines.append(f"- Risk level: **{risk}**.")
        return "\n".join(lines)
