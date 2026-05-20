from typing import Literal

from pydantic import Field

from app.api.schemas.common import APIModel


class RagQueryRequest(APIModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    source_type: Literal["project_doc", "github_issue"] | None = None


class RagRetrievedChunk(APIModel):
    chunk_id: str
    source_id: str
    title: str | None = None
    parent_title: str | None = None
    source_type: str
    score: float
    text_preview: str
    metadata: dict = Field(default_factory=dict)


class RagQueryResponse(APIModel):
    answer: str
    citations: list[str]
    chunks: list[RagRetrievedChunk]
    retrieval_mode: str
    embedding_model: str
