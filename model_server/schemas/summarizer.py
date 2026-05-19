"""Pydantic contracts for summarization."""

from pydantic import BaseModel


class SummarizeResponse(BaseModel):
    status: str
    feature: str
