import httpx
import pytest

from app.domain.rag import RetrievedChunk
from app.infra.exceptions import ToolFailure
from app.services.rag_service import RagService


class FakeRepository:
    def __init__(self):
        self.calls = []

    async def search_hybrid(self, *, query_text, query_embedding, embedding_model, top_k, source_type=None):
        self.calls.append((query_text, query_embedding, embedding_model, top_k, source_type))
        return [
            RetrievedChunk(
                chunk_id="chunk-1",
                source_id="project-doc:docs/DECISIONS.md",
                title="Decisions",
                parent_title="RAG embedding model choice",
                text="Use intfloat/e5-small-v2 as the first dense embedding model for RAG.",
                source_type="project_doc",
                score=0.99,
                dense_score=0.88,
                sparse_score=0.77,
                metadata={"path": "docs/DECISIONS.md"},
            )
        ]


@pytest.mark.asyncio
async def test_rag_service_embeds_query_and_searches_pgvector(monkeypatch):
    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json):
            if url.endswith("/embed"):
                assert json == {"texts": ["Which embedding model?"], "input_type": "query"}
                return httpx.Response(
                    200,
                    request=httpx.Request("POST", url),
                    json={
                        "embeddings": [[0.1, 0.2, 0.3]],
                        "model_name": "intfloat/e5-small-v2",
                        "dimensions": 3,
                        "input_type": "query",
                    },
                )
            assert url == "http://model-server:8001/rag-answer"
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "answer": "Use intfloat/e5-small-v2 for RAG embeddings.",
                    "citations": ["project-doc:docs/DECISIONS.md"],
                    "model_name": "gpt-4o-mini",
                    "provider": "openai",
                    "response_id": "resp_fake",
                },
            )

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    repository = FakeRepository()
    service = RagService(
        model_server_url="http://model-server:8001",
        database_url="postgresql://ignored",
        repository=repository,
    )

    result = await service.query(question="Which embedding model?", top_k=3, source_type="project_doc")

    assert repository.calls == [("Which embedding model?", [0.1, 0.2, 0.3], "intfloat/e5-small-v2", 3, "project_doc")]
    assert result.embedding_model == "intfloat/e5-small-v2"
    assert result.answer == "Use intfloat/e5-small-v2 for RAG embeddings."
    assert result.answer_provider == "openai"
    assert result.answer_model == "gpt-4o-mini"
    assert result.citations == ["project-doc:docs/DECISIONS.md"]
    assert result.retrieval_mode == "pgvector_hybrid_dense_sparse_e5"
    assert result.chunks[0].dense_score == 0.88
    assert result.chunks[0].sparse_score == 0.77
    assert result.chunks[0].text_preview.startswith("Use intfloat/e5-small-v2")


@pytest.mark.asyncio
async def test_rag_service_wraps_embedding_errors(monkeypatch):
    class FakeAsyncClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json):
            raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    service = RagService(model_server_url="http://model-server:8001", database_url="postgresql://ignored")

    with pytest.raises(ToolFailure):
        await service.query(question="hello", top_k=3)


@pytest.mark.asyncio
async def test_rag_service_falls_back_when_answer_generation_fails(monkeypatch):
    class FakeAsyncClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json):
            if url.endswith("/embed"):
                return httpx.Response(
                    200,
                    request=httpx.Request("POST", url),
                    json={
                        "embeddings": [[0.1, 0.2, 0.3]],
                        "model_name": "intfloat/e5-small-v2",
                        "dimensions": 3,
                        "input_type": "query",
                    },
                )
            return httpx.Response(503, request=httpx.Request("POST", url), json={"detail": "missing key"})

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    repository = FakeRepository()
    service = RagService(
        model_server_url="http://model-server:8001",
        database_url="postgresql://ignored",
        repository=repository,
    )

    result = await service.query(question="Which embedding model?", top_k=3)

    assert result.answer_provider == "retrieval-only"
    assert result.answer.startswith("I found relevant project context")
    assert result.citations == ["project-doc:docs/DECISIONS.md"]
