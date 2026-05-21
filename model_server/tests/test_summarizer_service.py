import os

import pytest

from model_server.schemas.summarizer import SummarizeRequest
from model_server.services import summarizer
from model_server.services.summarizer import OpenAIKeyMissingError, summarize_with_client


class FakeResponses:
    def parse(self, model, input, text_format):
        parsed = text_format(
            summary="read_csv crashes when loading empty CSV files.",
            key_points=["Function: read_csv", "Observed: unexpected exception"],
            affected_entities=["read_csv", "CSV"],
            maintainer_next_steps=["Confirm reproduction and expected behavior."],
            risk_level="medium",
        )
        return type("FakeResponse", (), {"output_parsed": parsed, "id": "resp_fake"})()


class FakeClient:
    responses = FakeResponses()


def test_summarize_with_client_returns_structured_summary():
    parsed, response_id = summarize_with_client(
        client=FakeClient(),
        payload=SummarizeRequest(
            title="BUG: read_csv crashes on empty file",
            body="read_csv raises an unexpected exception when the CSV has no rows.",
        ),
        model="gpt-4o-mini",
    )

    assert response_id == "resp_fake"
    assert parsed.summary.startswith("read_csv crashes")
    assert parsed.risk_level == "medium"


def test_summarizer_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    summarizer.get_summarizer.cache_clear()

    with pytest.raises(OpenAIKeyMissingError):
        summarizer.summarizer_api_key()


def test_summarizer_accepts_openai_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    assert summarizer.summarizer_api_key() == "test-key"


def test_summarizer_accepts_vault_llm_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setattr(summarizer, "runtime_secret_value", lambda key: "vault-key")

    assert summarizer.summarizer_api_key() == "vault-key"
