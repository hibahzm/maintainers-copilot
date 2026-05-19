"""Pydantic contracts for the issue-classifier endpoint."""

from pydantic import BaseModel, Field


class ClassifyIssueRequest(BaseModel):
    """Minimal issue fields needed for single-label maintainer triage."""

    title: str = Field(min_length=1, max_length=300)
    body: str = ""


class ClassifyIssueResponse(BaseModel):
    """Classifier output with softmax confidence and all label scores."""

    label: str = Field(description="One of: bug, feature, docs, question.")
    confidence: float = Field(ge=0.0, le=1.0)
    scores: dict[str, float]
    model_name: str
    model_dir: str
