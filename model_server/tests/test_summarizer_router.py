from fastapi.testclient import TestClient

from model_server.main import app
from model_server.schemas.summarizer import SummarizeResponse
from model_server.routers import summarizer as summarizer_router


def test_summarize_endpoint_returns_model_summary(monkeypatch):
    def fake_summarize(payload):
        return SummarizeResponse(
            summary="read_csv crashes on empty CSV files.",
            key_points=["Observed unexpected exception"],
            affected_entities=["read_csv", "CSV"],
            maintainer_next_steps=["Confirm reproduction"],
            risk_level="medium",
            model_name="gpt-4o-mini",
            response_id="resp_fake",
        )

    monkeypatch.setattr(summarizer_router, "summarize", fake_summarize)

    client = TestClient(app)
    response = client.post(
        "/summarize",
        json={"title": "BUG: read_csv crashes", "body": "CSV with no rows raises."},
    )

    assert response.status_code == 200
    assert response.json()["summary"] == "read_csv crashes on empty CSV files."
