"""Pydantic contracts for issue summarization."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class SummarizeRequest(BaseModel):
    """Issue text to summarize for maintainer triage."""

    title: str = Field(default="", max_length=300)
    body: str = ""
    text: str | None = Field(default=None, description="Optional pre-combined issue text.")

    @model_validator(mode="after")
    def require_some_text(self) -> "SummarizeRequest":
        if not any(part.strip() for part in (self.title, self.body, self.text or "")):
            raise ValueError("Provide title, body, or text for summarization.")
        return self


class SummarizeResponse(BaseModel):
    summary: str
    key_points: list[str]
    affected_entities: list[str]
    maintainer_next_steps: list[str]
    risk_level: Literal["low", "medium", "high"] = Field(description="One of: low, medium, high.")
    model_name: str
    provider: str = "openai"
    response_id: str | None = None
