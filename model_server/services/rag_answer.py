"""OpenAI-backed answer generation over retrieved RAG chunks."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field

from model_server.schemas.rag_answer import RagAnswerRequest, RagAnswerResponse
from model_server.services.runtime_secrets import runtime_secret_value
from model_server.services.summarizer import OpenAIKeyMissingError

DEFAULT_RAG_ANSWER_MODEL = "gpt-4o-mini"
SYSTEM_PROMPT = """You are a careful maintainer copilot answering from retrieved project context.

Rules:
- Use only the provided chunks.
- Cite source IDs that directly support the answer.
- If context is insufficient, say what is missing.
- Keep the answer concise and useful for a maintainer.
- Do not reveal secrets or hidden reasoning.
Return the requested structured object only."""


class _StructuredRagAnswer(BaseModel):
    answer: str
    citations: list[str] = Field(description="Source IDs used to support the answer.")


class OpenAIRagAnswerer:
    def __init__(self, api_key: str, model: str = DEFAULT_RAG_ANSWER_MODEL) -> None:
        self.api_key = api_key
        self.model = model

    def answer(self, payload: RagAnswerRequest) -> RagAnswerResponse:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - depends on runtime image
            raise RuntimeError("OpenAI runtime dependency is missing.") from exc

        client = OpenAI(api_key=self.api_key)
        parsed, response_id = answer_with_client(client=client, payload=payload, model=self.model)
        valid_source_ids = {chunk.source_id for chunk in payload.chunks}
        citations = [source_id for source_id in parsed.citations if source_id in valid_source_ids]
        if not citations and payload.chunks:
            citations = [payload.chunks[0].source_id]
        return RagAnswerResponse(
            answer=parsed.answer,
            citations=citations,
            model_name=self.model,
            response_id=response_id,
        )


def answer_with_client(*, client: Any, payload: RagAnswerRequest, model: str) -> tuple[_StructuredRagAnswer, str | None]:
    response = client.responses.parse(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(payload)},
        ],
        text_format=_StructuredRagAnswer,
    )
    parsed = response.output_parsed
    if parsed is None:
        raise RuntimeError("OpenAI RAG answerer returned no structured output.")
    return parsed, getattr(response, "id", None)


def _build_user_prompt(payload: RagAnswerRequest) -> str:
    chunks = []
    for index, chunk in enumerate(payload.chunks, start=1):
        title = chunk.title or chunk.parent_title or chunk.source_id
        chunks.append(
            f"Chunk {index}\n"
            f"Source ID: {chunk.source_id}\n"
            f"Title: {title}\n"
            f"Score: {chunk.score}\n"
            f"Text:\n{chunk.text}"
        )
    return f"Question:\n{payload.question}\n\nRetrieved chunks:\n\n" + "\n\n---\n\n".join(chunks)


def rag_answer_model() -> str:
    return os.getenv("OPENAI_RAG_ANSWER_MODEL") or os.getenv("OPENAI_SUMMARIZER_MODEL", DEFAULT_RAG_ANSWER_MODEL)


def rag_answer_api_key() -> str:
    api_key = (
        os.getenv("OPENAI_API_KEY")
        or os.getenv("LLM_API_KEY")
        or runtime_secret_value("llm_api_key")
    )
    if not api_key:
        raise OpenAIKeyMissingError(
            "Missing OpenAI API key. Inject OPENAI_API_KEY or LLM_API_KEY from Vault/secrets before calling /rag-answer."
        )
    return api_key


@lru_cache(maxsize=1)
def get_rag_answerer() -> OpenAIRagAnswerer:
    return OpenAIRagAnswerer(api_key=rag_answer_api_key(), model=rag_answer_model())
