"""FastAPI router for summarization."""

from fastapi import APIRouter

from model_server.schemas.summarizer import SummarizeResponse
from model_server.services.summarizer import summarize

router = APIRouter(tags=["summarizer"])


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_endpoint() -> SummarizeResponse:
    return summarize()
