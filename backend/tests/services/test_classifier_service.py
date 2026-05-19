import httpx
import pytest

from app.api.schemas.classifier import ClassifyIssueResponse
from app.infra.exceptions import ToolFailure
from app.services.classifier_service import ClassifierService


@pytest.mark.asyncio
async def test_classifier_service_normalizes_model_server_response(monkeypatch):
    requests = []

    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json):
            requests.append((url, json, self.timeout))
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "label": "docs",
                    "confidence": 0.87,
                    "scores": {"bug": 0.01, "feature": 0.05, "docs": 0.87, "question": 0.07},
                    "model_name": "first-distilbert-freeze4",
                    "model_dir": "/models/classifier",
                    "model_artifact_sha256": "abc123",
                },
            )

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    service = ClassifierService(model_server_url="http://model-server:8001/")
    result = await service.classify_issue(title="DOC: typo", body="Small docs typo")

    assert isinstance(result, ClassifyIssueResponse)
    assert result.label == "docs"
    assert result.confidence == 0.87
    assert result.model_artifact_sha256 == "abc123"
    assert requests == [
        (
            "http://model-server:8001/classify",
            {"title": "DOC: typo", "body": "Small docs typo"},
            10.0,
        )
    ]


@pytest.mark.asyncio
async def test_classifier_service_wraps_http_errors(monkeypatch):
    class FakeAsyncClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json):
            raise httpx.ConnectError("no server")

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    service = ClassifierService(model_server_url="http://model-server:8001")
    with pytest.raises(ToolFailure):
        await service.classify_issue(title="BUG: crash", body="boom")
