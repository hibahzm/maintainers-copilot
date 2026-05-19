"""Pydantic contracts for code-shaped named-entity extraction."""

from pydantic import BaseModel, Field, model_validator


class NERRequest(BaseModel):
    """Issue text to inspect for maintainer/code-shaped entities."""

    title: str = Field(default="", max_length=300)
    body: str = ""
    text: str | None = Field(
        default=None,
        description="Optional pre-combined text. If provided, title/body are still accepted as context.",
    )

    @model_validator(mode="after")
    def require_some_text(self) -> "NERRequest":
        if not any(part.strip() for part in (self.title, self.body, self.text or "")):
            raise ValueError("Provide title, body, or text for entity extraction.")
        return self


class CodeEntity(BaseModel):
    """One extracted code-shaped entity and its character span."""

    type: str
    text: str
    normalized: str
    start: int
    end: int


class NERResponse(BaseModel):
    entities: list[CodeEntity]
    grouped: dict[str, list[str]]
    extractor: str = "rule-based-code-entity-extractor"
    tokenizer_backend: str
