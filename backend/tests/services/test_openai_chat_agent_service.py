import json

import httpx
import pytest
from pydantic import SecretStr

from app.api.schemas.classifier import ClassifyIssueResponse
from app.api.schemas.rag import RagQueryResponse
from app.services.chat_agent.openai_agent import OpenAIChatAgentService
from app.services.chat_tools.runner import ChatToolRunner


class FakeRagService:
    async def query(self, *, question, top_k, source_type=None, generate_answer=True):
        return RagQueryResponse(
            answer="retrieval-only",
            citations=["project-doc:docs/DECISIONS.md"],
            chunks=[],
            retrieval_mode="pgvector_hybrid_dense_sparse_e5",
            embedding_model="intfloat/e5-small-v2",
            answer_provider="retrieval-only",
        )


class FakeToolsService:
    async def classify_issue(self, *, title, body):
        return ClassifyIssueResponse(
            label="bug",
            confidence=0.91,
            scores={"bug": 0.91, "docs": 0.03, "feature": 0.04, "question": 0.02},
            model_name="fake",
        )


@pytest.mark.asyncio
async def test_openai_agent_executes_tool_call_and_returns_final_answer():
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        requests.append(payload)
        if len(requests) == 1:
            return httpx.Response(
                200,
                json={
                    "id": "resp_1",
                    "output": [
                        {
                            "type": "function_call",
                            "call_id": "call_1",
                            "name": "classify_issue",
                            "arguments": json.dumps(
                                {"title": "read_csv crash", "body": "raises ValueError"}
                            ),
                        }
                    ],
                },
            )
        return httpx.Response(
            200,
            json={
                "id": "resp_2",
                "output_text": "This is a bug with high confidence.",
                "output": [],
            },
        )

    agent = OpenAIChatAgentService(
        api_key=SecretStr("test-key"),
        model="gpt-4o-mini",
        rag_service=FakeRagService(),
        tool_runner=ChatToolRunner(tools_service=FakeToolsService()),
        transport=httpx.MockTransport(handler),
        base_url="https://api.test",
    )

    result = await agent.respond(
        user_id=None,
        messages=[{"role": "user", "content": "Classify this issue"}],
        use_rag=True,
        top_k=5,
        allow_summarizer=False,
        allow_memory_write=False,
    )

    assert result.answer == "This is a bug with high confidence."
    assert result.tool_results[0].name == "classifier.classify"
    assert result.tool_results[0].metadata["label"] == "bug"
    assert requests[1]["previous_response_id"] == "resp_1"
    assert requests[1]["input"][0]["type"] == "function_call_output"


@pytest.mark.asyncio
async def test_openai_agent_rag_tool_returns_citations():
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        if "previous_response_id" not in payload:
            return httpx.Response(
                200,
                json={
                    "id": "resp_1",
                    "output": [
                        {
                            "type": "function_call",
                            "call_id": "call_1",
                            "name": "rag_search",
                            "arguments": json.dumps(
                                {"query": "embedding choice", "top_k": 5, "source_type": "any"}
                            ),
                        }
                    ],
                },
            )
        return httpx.Response(200, json={"id": "resp_2", "output_text": "Use E5."})

    agent = OpenAIChatAgentService(
        api_key=SecretStr("test-key"),
        model="gpt-4o-mini",
        rag_service=FakeRagService(),
        tool_runner=ChatToolRunner(),
        transport=httpx.MockTransport(handler),
        base_url="https://api.test",
    )

    result = await agent.respond(
        user_id=None,
        messages=[{"role": "user", "content": "What embedding did we choose?"}],
        use_rag=True,
        top_k=5,
        allow_summarizer=False,
        allow_memory_write=False,
    )

    assert result.answer == "Use E5."
    assert result.citations == ["project-doc:docs/DECISIONS.md"]
    assert result.tool_results[0].name == "rag.query"
