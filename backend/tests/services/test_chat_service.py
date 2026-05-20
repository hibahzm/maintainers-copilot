import pytest

from app.api.schemas.classifier import ClassifyIssueResponse
from app.api.schemas.rag import RagQueryResponse
from app.domain.chat import Message
from app.services.chat_service import ChatService
from app.services.chat_tools.runner import ChatToolRunner


class FakeRagService:
    async def query(self, *, question, top_k, generate_answer=True, source_type=None):
        return RagQueryResponse(
            answer=f"Grounded answer for: {question}",
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

    async def extract_entities(self, *, title, body, text=None):
        return {
            "entities": [],
            "grouped": {"function": ["read_csv"]},
            "extractor": "fake",
            "tokenizer_backend": "regex",
        }


class FakeConversationStateService:
    def __init__(self, messages=None):
        self.messages = messages or []
        self.saved_conversation_id = None
        self.saved_messages = []

    async def load_messages(self, conversation_id):
        return self.messages

    async def save_messages(self, conversation_id, messages):
        self.saved_conversation_id = conversation_id
        self.saved_messages = messages


@pytest.mark.asyncio
async def test_chat_service_uses_rag_for_latest_user_message():
    service = ChatService(rag_service=FakeRagService())

    response = await service.respond(
        conversation_id="conv-1",
        messages=[Message(role="user", content="Which embedding model did we choose?")],
        top_k=3,
    )

    assert response.conversation_id == "conv-1"
    assert response.message.role == "assistant"
    assert response.message.content == "Grounded answer for: Which embedding model did we choose?"
    assert response.citations == ["project-doc:docs/DECISIONS.md"]
    assert response.tool_results[0].name == "rag.query"


@pytest.mark.asyncio
async def test_chat_service_saves_short_term_conversation_state():
    state = FakeConversationStateService(
        messages=[
            Message(role="user", content="first turn"),
            Message(role="assistant", content="first answer"),
        ]
    )
    service = ChatService(rag_service=FakeRagService(), conversation_state_service=state)

    response = await service.respond(
        conversation_id="conv-1",
        messages=[Message(role="user", content="second turn")],
    )

    assert response.conversation_id == "conv-1"
    assert state.saved_conversation_id == "conv-1"
    assert [message.content for message in state.saved_messages] == [
        "first turn",
        "first answer",
        "second turn",
        "Grounded answer for: second turn",
    ]


@pytest.mark.asyncio
async def test_chat_service_routes_explicit_issue_tools_before_rag():
    service = ChatService(
        rag_service=FakeRagService(),
        tool_runner=ChatToolRunner(tools_service=FakeToolsService()),
    )

    response = await service.respond(
        conversation_id="conv-1",
        messages=[
            Message(
                role="user",
                content="Classify and extract entities:\nread_csv crashes on empty CSV",
            )
        ],
        top_k=3,
    )

    assert "Classification" in response.message.content
    assert "Extracted entities" in response.message.content
    assert [tool.name for tool in response.tool_results] == [
        "classifier.classify",
        "ner.extract",
    ]


@pytest.mark.asyncio
async def test_chat_service_blocks_memory_write_without_explicit_permission():
    service = ChatService(
        rag_service=FakeRagService(),
        tool_runner=ChatToolRunner(),
    )

    response = await service.respond(
        conversation_id="conv-1",
        messages=[Message(role="user", content="Remember that I prefer concise answers")],
        tools=["write_memory"],
    )

    assert "Memory was not saved" in response.message.content
    assert response.tool_results[0].name == "memory.write"
    assert response.tool_results[0].status == "blocked"


@pytest.mark.asyncio
async def test_chat_service_handles_missing_user_message():
    service = ChatService(rag_service=FakeRagService())

    response = await service.respond(
        conversation_id=None,
        messages=[Message(role="assistant", content="hi")],
    )

    assert response.message.content.startswith("Send me")
    assert response.conversation_id
