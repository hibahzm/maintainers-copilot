"""Chat orchestration over the project's tools."""

from typing import Literal
from uuid import uuid4

from app.api.schemas.chat import ChatResponse, ChatToolResult
from app.domain.chat import Message
from app.infra.exceptions import ToolFailure
from app.services.maintainer_tools_service import MaintainerToolsService
from app.services.rag_service import RagService

ChatToolName = Literal["auto", "rag", "classifier", "ner", "summarizer"]


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
    ) -> None:
        self.rag_service = rag_service
        self.tools_service = tools_service

    async def respond(
        self,
        *,
        messages: list[Message],
        conversation_id: str | None,
        use_rag: bool = True,
        top_k: int = 5,
        allow_summarizer: bool = False,
        tools: list[ChatToolName] | None = None,
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

        selected_tools = self._select_tools(
            latest_user_message.content,
            tools=tools or ["auto"],
            use_rag=use_rag,
            allow_summarizer=allow_summarizer,
        )
        tool_results = await self._run_issue_tools(
            latest_user_message.content,
            selected_tools=selected_tools,
            allow_summarizer=allow_summarizer,
        )
        if tool_results:
            return ChatResponse(
                conversation_id=response_conversation_id,
                message=Message(
                    role="assistant",
                    content=self._render_tool_answer(tool_results),
                ),
                tool_results=tool_results,
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
                entities = await self.tools_service.extract_entities(title=title, body=body, text=text)
                results.append(
                    ChatToolResult(name="ner.extract", status="ok", metadata=entities)
                )
            except ToolFailure as exc:
                results.append(
                    ChatToolResult(name="ner.extract", status="failed", metadata={"error": str(exc)})
                )

        if "summarizer" in selected_tools and allow_summarizer:
            try:
                summary = await self.tools_service.summarize_issue(title=title, body=body, text=text)
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

    def _latest_user_message(self, messages: list[Message]) -> Message | None:
        for message in reversed(messages):
            if message.role == "user" and message.content.strip():
                return message
        return None

    def _select_tools(
        self,
        text: str,
        *,
        tools: list[ChatToolName],
        use_rag: bool,
        allow_summarizer: bool,
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

    def _render_tool_answer(self, tool_results: list[ChatToolResult]) -> str:
        lines = ["Here is the tool output for this issue:"]
        for result in tool_results:
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
