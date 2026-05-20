from model_server.main import app
from model_server.routers import rag_answer as rag_answer_router
from model_server.schemas.rag_answer import RagAnswerResponse


class FakeRagAnswerer:
    def answer(self, payload):
        return RagAnswerResponse(
            answer="Use intfloat/e5-small-v2 for RAG embeddings.",
            citations=[payload.chunks[0].source_id],
            model_name="fake-openai",
            response_id="resp_fake",
        )


def test_rag_answer_endpoint(monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setattr(rag_answer_router, "get_rag_answerer", lambda: FakeRagAnswerer())
    client = TestClient(app)

    response = client.post(
        "/rag-answer",
        json={
            "question": "Which embedding model?",
            "chunks": [
                {
                    "source_id": "project-doc:docs/DECISIONS.md",
                    "title": "Decisions",
                    "text": "Use intfloat/e5-small-v2 as the first dense embedding model for RAG.",
                    "score": 0.99,
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["citations"] == ["project-doc:docs/DECISIONS.md"]
