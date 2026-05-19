from fastapi.testclient import TestClient

from model_server.routers import classifier as classifier_router
from model_server.schemas.classifier import ClassifyIssueResponse
from model_server.main import app


class FakeClassifier:
    def predict(self, *, title: str, body: str):
        return ClassifyIssueResponse(
            label="bug",
            confidence=0.91,
            scores={"bug": 0.91, "feature": 0.03, "docs": 0.02, "question": 0.04},
            model_name="fake-distilbert",
            model_dir="/tmp/fake-model",
        )


def test_classify_endpoint_returns_model_prediction(monkeypatch):
    monkeypatch.setattr(classifier_router, "get_classifier", lambda: FakeClassifier())

    client = TestClient(app)
    response = client.post(
        "/classify",
        json={"title": "BUG: crash while reading CSV", "body": "read_csv raises unexpectedly"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "label": "bug",
        "confidence": 0.91,
        "scores": {"bug": 0.91, "feature": 0.03, "docs": 0.02, "question": 0.04},
        "model_name": "fake-distilbert",
        "model_dir": "/tmp/fake-model",
    }


def test_classify_endpoint_reports_missing_model(monkeypatch):
    class MissingModel:
        def predict(self, *, title: str, body: str):
            raise FileNotFoundError("missing model")

    monkeypatch.setattr(classifier_router, "get_classifier", lambda: MissingModel())

    client = TestClient(app)
    response = client.post("/classify", json={"title": "Question", "body": "How do I use this?"})

    assert response.status_code == 503
    assert "missing model" in response.json()["detail"]
