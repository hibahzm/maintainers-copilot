import pytest

from app.api.schemas.rag import RagQueryResponse
from app.domain.chat import Message
from app.services.chat_service import ChatService


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
async def test_chat_service_handles_missing_user_message():
    service = ChatService(rag_service=FakeRagService())

    response = await service.respond(conversation_id=None, messages=[Message(role="assistant", content="hi")])

    assert response.message.content.startswith("Send me")
    assert response.conversation_id
