"""Pydantic contracts for text embedding endpoint."""

from typing import Literal

from pydantic import BaseModel, Field


class EmbedTextRequest(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=32)
    input_type: Literal["query", "passage"] = "query"


class EmbedTextResponse(BaseModel):
    embeddings: list[list[float]]
    model_name: str
    dimensions: int
    input_type: Literal["query", "passage"]
