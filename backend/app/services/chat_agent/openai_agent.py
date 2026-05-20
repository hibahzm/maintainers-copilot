"""Bounded OpenAI tool-calling agent for maintainer chat."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
from pydantic import SecretStr

from app.api.schemas.chat import ChatToolResult
from app.infra.exceptions import ToolFailure
from app.services.chat_tools.runner import ChatToolRunner
from app.services.rag_service import RagService

_PROMPT_PATH = Path(__file__).with_name("prompts") / "agent_system.txt"


@lru_cache(maxsize=1)
def agent_system_prompt() -> str:
    """Load the chat-agent system prompt from the backend-local prompt file."""
    return _PROMPT_PATH.read_text(encoding="utf-8").strip()


@dataclass
class AgentRunResult:
    answer: str
    citations: list[str] = field(default_factory=list)
    tool_results: list[ChatToolResult] = field(default_factory=list)
    response_id: str | None = None


class OpenAIChatAgentService:
    """Run a bounded Responses API function-calling loop."""

    def __init__(
        self,
        *,
        api_key: SecretStr | None,
        model: str,
        rag_service: RagService,
        tool_runner: ChatToolRunner,
        max_tool_rounds: int = 3,
        timeout_seconds: float = 30.0,
        base_url: str = "https://api.openai.com/v1",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.rag_service = rag_service
        self.tool_runner = tool_runner
        self.max_tool_rounds = max_tool_rounds
        self.timeout_seconds = timeout_seconds
        self.base_url = base_url.rstrip("/")
        self.transport = transport

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.get_secret_value())

    async def respond(
        self,
        *,
        user_id: UUID | None,
        messages: list[dict[str, str]],
        use_rag: bool,
        top_k: int,
        allow_summarizer: bool,
        allow_memory_write: bool,
    ) -> AgentRunResult:
        if not self.is_configured:
            raise ToolFailure("OpenAI chat agent is not configured.")

        tool_schemas = self._tool_schemas(
            use_rag=use_rag,
            allow_summarizer=allow_summarizer,
            allow_memory_write=allow_memory_write,
        )
        response = await self._create_response(
            input_payload=self._conversation_input(messages),
            tools=tool_schemas,
        )
        tool_results: list[ChatToolResult] = []
        citations: list[str] = []

        for _round in range(self.max_tool_rounds):
            calls = self._function_calls(response)
            if not calls:
                return AgentRunResult(
                    answer=self._extract_text(response),
                    citations=citations,
                    tool_results=tool_results,
                    response_id=response.get("id"),
                )

            function_outputs = []
            for call in calls:
                output, result = await self._execute_tool_call(
                    call,
                    user_id=user_id,
                    default_top_k=top_k,
                    allow_summarizer=allow_summarizer,
                    allow_memory_write=allow_memory_write,
                )
                if result is not None:
                    tool_results.append(result)
                    citations.extend(result.citations)
                function_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.get("call_id", ""),
                        "output": json.dumps(output, ensure_ascii=False),
                    }
                )

            response = await self._create_response(
                input_payload=function_outputs,
                tools=tool_schemas,
                previous_response_id=response.get("id"),
            )

        final_text = self._extract_text(response)
        if not final_text:
            final_text = (
                "I reached the tool-call limit before a final answer. "
                "Here are the tool results I found."
            )
        return AgentRunResult(
            answer=final_text,
            citations=list(dict.fromkeys(citations)),
            tool_results=tool_results,
            response_id=response.get("id"),
        )

    async def _execute_tool_call(
        self,
        call: dict[str, Any],
        *,
        user_id: UUID | None,
        default_top_k: int,
        allow_summarizer: bool,
        allow_memory_write: bool,
    ) -> tuple[dict[str, Any], ChatToolResult | None]:
        name = str(call.get("name", ""))
        try:
            args = json.loads(call.get("arguments") or "{}")
        except (TypeError, json.JSONDecodeError):
            return {"status": "error", "error": "Invalid JSON tool arguments."}, None

        if name == "rag_search":
            return await self._run_rag_search(args, default_top_k=default_top_k)

        tool_name_map = {
            "classify_issue": "classifier",
            "extract_entities": "ner",
            "summarize_issue": "summarizer",
            "write_memory": "write_memory",
        }
        selected_tool = tool_name_map.get(name)
        if selected_tool is None:
            return {"status": "error", "error": f"Unknown tool: {name}"}, None

        text = self._tool_text(name, args)
        results = await self.tool_runner.run(
            text,
            user_id=user_id,
            tools=[selected_tool],
            use_rag=False,
            allow_summarizer=allow_summarizer,
            allow_memory_write=allow_memory_write,
        )
        if not results:
            return {"status": "skipped", "tool": name}, None

        result = results[0]
        output = {"status": result.status, "tool": result.name, "data": result.metadata}
        return output, result

    async def _run_rag_search(
        self,
        args: dict[str, Any],
        *,
        default_top_k: int,
    ) -> tuple[dict[str, Any], ChatToolResult]:
        question = str(args.get("query") or "").strip()
        if not question:
            output = {"status": "error", "error": "rag_search requires a query."}
            return output, ChatToolResult(name="rag.query", status="failed", metadata=output)

        source_type = args.get("source_type")
        if source_type == "any":
            source_type = None
        top_k = args.get("top_k") or default_top_k
        try:
            rag_response = await self.rag_service.query(
                question=question,
                top_k=max(1, min(int(top_k), 10)),
                source_type=source_type,
                generate_answer=False,
            )
        except (TypeError, ValueError, ToolFailure) as exc:
            output = {"status": "error", "error": str(exc)}
            return output, ChatToolResult(name="rag.query", status="failed", metadata=output)

        output = {
            "status": "ok",
            "answer": rag_response.answer,
            "citations": rag_response.citations,
            "chunks": [chunk.model_dump(mode="json") for chunk in rag_response.chunks],
            "retrieval_mode": rag_response.retrieval_mode,
            "embedding_model": rag_response.embedding_model,
        }
        return output, ChatToolResult(
            name="rag.query",
            status="ok",
            citations=rag_response.citations,
            chunks=rag_response.chunks,
            metadata={
                "retrieval_mode": rag_response.retrieval_mode,
                "embedding_model": rag_response.embedding_model,
            },
        )

    def _tool_text(self, name: str, args: dict[str, Any]) -> str:
        if name == "write_memory":
            return str(args.get("content") or "")
        title = str(args.get("title") or "Untitled issue")
        body = str(args.get("body") or "")
        text = str(args.get("text") or "")
        if text and name in {"extract_entities", "summarize_issue"}:
            return text
        return f"{title}\n{body}".strip()

    async def _create_response(
        self,
        *,
        input_payload: str | list[dict[str, Any]],
        tools: list[dict[str, Any]],
        previous_response_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "instructions": agent_system_prompt(),
            "input": input_payload,
            "tools": tools,
            "parallel_tool_calls": True,
            "max_output_tokens": 700,
        }
        if previous_response_id:
            payload["previous_response_id"] = previous_response_id

        headers = {
            "Authorization": f"Bearer {self.api_key.get_secret_value() if self.api_key else ''}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post("/responses", headers=headers, json=payload)
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                return data
        except httpx.HTTPError as exc:
            raise ToolFailure("OpenAI chat agent request failed.") from exc
        except ValueError as exc:
            raise ToolFailure("OpenAI chat agent returned invalid JSON.") from exc

    def _conversation_input(self, messages: list[dict[str, str]]) -> str:
        lines = []
        for message in messages[-12:]:
            role = message.get("role", "user")
            content = message.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _function_calls(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        calls = []
        for item in response.get("output") or []:
            if item.get("type") == "function_call":
                calls.append(item)
        return calls

    def _extract_text(self, response: dict[str, Any]) -> str:
        if response.get("output_text"):
            return str(response["output_text"])
        parts: list[str] = []
        for item in response.get("output") or []:
            if item.get("type") != "message":
                continue
            for content in item.get("content") or []:
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    parts.append(str(content["text"]))
        return "\n".join(parts).strip()

    def _tool_schemas(
        self,
        *,
        use_rag: bool,
        allow_summarizer: bool,
        allow_memory_write: bool,
    ) -> list[dict[str, Any]]:
        tools = []
        if use_rag:
            tools.append(
                _function_tool(
                    "rag_search",
                    "Search the project RAG corpus and return grounded chunks/citations.",
                    {
                        "query": {"type": "string", "description": "The search query."},
                        "top_k": {"type": "integer", "minimum": 1, "maximum": 10},
                        "source_type": {
                            "type": "string",
                            "enum": ["any", "project_doc", "github_issue"],
                        },
                    },
                    ["query", "top_k", "source_type"],
                )
            )
        tools.extend(
            [
                _function_tool(
                    "classify_issue",
                    "Classify an issue as bug, feature, docs, or question.",
                    {
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                    },
                    ["title", "body"],
                ),
                _function_tool(
                    "extract_entities",
                    "Extract code-shaped entities from issue text.",
                    {
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                        "text": {"type": "string"},
                    },
                    ["title", "body", "text"],
                ),
            ]
        )
        if allow_summarizer:
            tools.append(
                _function_tool(
                    "summarize_issue",
                    "Summarize issue text for maintainer triage.",
                    {
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                        "text": {"type": "string"},
                    },
                    ["title", "body", "text"],
                )
            )
        if allow_memory_write:
            tools.append(
                _function_tool(
                    "write_memory",
                    "Explicitly save a user-approved long-term memory.",
                    {
                        "content": {"type": "string"},
                        "memory_type": {
                            "type": "string",
                            "enum": ["semantic", "episodic", "procedural"],
                        },
                    },
                    ["content", "memory_type"],
                )
            )
        return tools


def _function_tool(
    name: str,
    description: str,
    properties: dict[str, Any],
    required: list[str],
) -> dict[str, Any]:
    return {
        "type": "function",
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
        "strict": True,
    }
