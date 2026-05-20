"""Pydantic contracts for RAG answer generation."""

from pydantic import BaseModel, Field


class RagAnswerChunk(BaseModel):
    source_id: str
    title: str | None = None
    parent_title: str | None = None
    text: str = Field(min_length=1)
    score: float | None = None


class RagAnswerRequest(BaseModel):
    question: str = Field(min_length=1)
    chunks: list[RagAnswerChunk] = Field(min_length=1, max_length=10)


class RagAnswerResponse(BaseModel):
    answer: str
    citations: list[str]
    model_name: str
    provider: str = "openai"
    response_id: str | None = None
