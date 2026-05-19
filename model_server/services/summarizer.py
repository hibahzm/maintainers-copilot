"""Summarization service."""

from model_server.schemas.summarizer import SummarizeResponse


def summarize() -> SummarizeResponse:
    """Placeholder until the summarization pipeline is implemented."""
    return SummarizeResponse(status="todo", feature="summarization")
