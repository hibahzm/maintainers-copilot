from model_server.main import app
from model_server.schemas.embedder import EmbedTextResponse
from model_server.routers import embedder as embedder_router


class FakeEmbedder:
    def embed(self, texts, *, input_type):
        return EmbedTextResponse(
            embeddings=[[0.1, 0.2, 0.3] for _ in texts],
            model_name="fake-e5",
            dimensions=3,
            input_type=input_type,
        )


def test_embed_endpoint_returns_vectors(monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setattr(embedder_router, "get_embedder", lambda: FakeEmbedder())
    client = TestClient(app)

    response = client.post("/embed", json={"texts": ["hello"], "input_type": "query"})

    assert response.status_code == 200
    assert response.json() == {
        "embeddings": [[0.1, 0.2, 0.3]],
        "model_name": "fake-e5",
        "dimensions": 3,
        "input_type": "query",
    }
