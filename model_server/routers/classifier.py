"""FastAPI router for issue classification."""

from fastapi import APIRouter, HTTPException, status

from model_server.schemas.classifier import ClassifyIssueRequest, ClassifyIssueResponse
from model_server.services.classifier import get_classifier

router = APIRouter(tags=["classifier"])


@router.post("/classify", response_model=ClassifyIssueResponse)
async def classify(payload: ClassifyIssueRequest) -> ClassifyIssueResponse:
    """Classify a GitHub issue title/body into the project label set."""
    try:
        return get_classifier().predict(title=payload.title, body=payload.body)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # noqa: BLE001 - keep model internals behind a 500 boundary
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Classifier inference failed.",
        ) from exc
