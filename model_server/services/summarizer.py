"""OpenAI-backed issue summarization service."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Literal

from pydantic import BaseModel

from model_server.schemas.summarizer import SummarizeRequest, SummarizeResponse

DEFAULT_SUMMARIZER_MODEL = "gpt-4o-mini"
SYSTEM_PROMPT = """You are a concise maintainer assistant for GitHub issues.

Summarize the issue for a busy open-source maintainer.
Use only the provided issue title/body/text.
Do not invent versions, stack traces, root causes, or affected files.
Prefer concrete maintainer language over generic product language.
If the issue is unclear, say what is unclear in maintainer_next_steps.
Return the requested structured object only."""


class _StructuredIssueSummary(BaseModel):
    summary: str
    key_points: list[str]
    affected_entities: list[str]
    maintainer_next_steps: list[str]
    risk_level: Literal["low", "medium", "high"]


class OpenAIKeyMissingError(RuntimeError):
    """Raised when the summarizer is called without an injected OpenAI key."""


class OpenAISummarizer:
    def __init__(self, api_key: str, model: str = DEFAULT_SUMMARIZER_MODEL) -> None:
        self.api_key = api_key
        self.model = model

    def summarize(self, payload: SummarizeRequest) -> SummarizeResponse:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - depends on runtime image
            raise RuntimeError("OpenAI runtime dependency is missing.") from exc

        client = OpenAI(api_key=self.api_key)
        parsed, response_id = summarize_with_client(client=client, payload=payload, model=self.model)
        return SummarizeResponse(
            summary=parsed.summary,
            key_points=parsed.key_points,
            affected_entities=parsed.affected_entities,
            maintainer_next_steps=parsed.maintainer_next_steps,
            risk_level=parsed.risk_level,
            model_name=self.model,
            response_id=response_id,
        )


def summarize_with_client(*, client: Any, payload: SummarizeRequest, model: str) -> tuple[_StructuredIssueSummary, str | None]:
    """Call a Responses API client and parse the structured issue summary."""
    response = client.responses.parse(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(payload)},
        ],
        text_format=_StructuredIssueSummary,
    )
    parsed = response.output_parsed
    if parsed is None:
        raise RuntimeError("OpenAI summarizer returned no structured output.")
    return parsed, getattr(response, "id", None)


def _build_user_prompt(payload: SummarizeRequest) -> str:
    parts = []
    if payload.title.strip():
        parts.append(f"Title:\n{payload.title.strip()}")
    if payload.body.strip():
        parts.append(f"Body:\n{payload.body.strip()}")
    if payload.text and payload.text.strip():
        parts.append(f"Additional text:\n{payload.text.strip()}")
    return "\n\n".join(parts)


def summarizer_model() -> str:
    return os.getenv("OPENAI_SUMMARIZER_MODEL", DEFAULT_SUMMARIZER_MODEL)


def summarizer_api_key() -> str:
    # Production should inject this from Vault/secret manager into the model-server runtime.
    # Colab/local experiments may use OPENAI_API_KEY directly.
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    if not api_key:
        raise OpenAIKeyMissingError(
            "Missing OpenAI API key. Inject OPENAI_API_KEY or LLM_API_KEY from Vault/secrets before calling /summarize."
        )
    return api_key


@lru_cache(maxsize=1)
def get_summarizer() -> OpenAISummarizer:
    return OpenAISummarizer(api_key=summarizer_api_key(), model=summarizer_model())


def summarize(payload: SummarizeRequest) -> SummarizeResponse:
    return get_summarizer().summarize(payload)
