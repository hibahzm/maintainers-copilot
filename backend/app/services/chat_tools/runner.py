"""Execute selected chat tools."""

from uuid import UUID

from app.api.schemas.chat import ChatToolResult
from app.api.schemas.memory import MemoryCreateRequest
from app.infra.exceptions import ToolFailure
from app.services.chat_tools.model_server_tools import MaintainerToolsService
from app.services.chat_tools.selector import select_tools
from app.services.chat_tools.text import memory_content, split_issue_text
from app.services.chat_tools.types import ChatToolName
from app.services.memory_service import MemoryService


class ChatToolRunner:
    """Run maintainer tools while keeping ChatService focused on orchestration."""

    def __init__(
        self,
        *,
        tools_service: MaintainerToolsService | None = None,
        memory_service: MemoryService | None = None,
    ) -> None:
        self.tools_service = tools_service
        self.memory_service = memory_service

    async def run(
        self,
        text: str,
        *,
        user_id: UUID | None,
        tools: list[ChatToolName],
        use_rag: bool,
        allow_summarizer: bool,
        allow_memory_write: bool,
    ) -> list[ChatToolResult]:
        selected_tools = select_tools(
            text,
            tools=tools,
            use_rag=use_rag,
            allow_summarizer=allow_summarizer,
            allow_memory_write=allow_memory_write,
        )
        memory_result = await self._run_memory_tool(
            text,
            user_id=user_id,
            selected_tools=selected_tools,
            allow_memory_write=allow_memory_write,
        )
        if memory_result is not None:
            return [memory_result]
        return await self._run_issue_tools(
            text,
            selected_tools=selected_tools,
            allow_summarizer=allow_summarizer,
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

        title, body = split_issue_text(text)
        results: list[ChatToolResult] = []

        if "classifier" in selected_tools:
            try:
                classification = await self.tools_service.classify_issue(
                    title=title,
                    body=body,
                )
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

        content = memory_content(text)
        try:
            record = await self.memory_service.write_memory(
                MemoryCreateRequest(
                    user_id=user_id,
                    content=content,
                    memory_type="semantic",
                )
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
