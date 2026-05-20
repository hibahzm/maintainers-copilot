"""Domain models for RAG retrieval."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    source_id: str
    title: str | None
    parent_title: str | None
    text: str
    source_type: str
    score: float
    dense_score: float = 0.0
    sparse_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
