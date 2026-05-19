"""FastAPI router for summarization."""

from fastapi import APIRouter, HTTPException, status

from model_server.schemas.summarizer import SummarizeRequest, SummarizeResponse
from model_server.services.summarizer import OpenAIKeyMissingError, summarize

router = APIRouter(tags=["summarizer"])


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_endpoint(payload: SummarizeRequest) -> SummarizeResponse:
    try:
        return summarize(payload)
    except OpenAIKeyMissingError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # noqa: BLE001 - keep provider details behind a stable API boundary
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Summarization failed.",
        ) from exc
