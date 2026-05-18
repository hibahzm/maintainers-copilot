from fastapi import APIRouter

from app.api.dependencies import ClassifierServiceDep
from app.api.schemas.classifier import ClassifyIssueRequest
from app.api.schemas.common import FeatureStubResponse

router = APIRouter(prefix="/classifier", tags=["classifier"])


@router.post("", response_model=FeatureStubResponse)
async def classify_issue(
    payload: ClassifyIssueRequest,
    service: ClassifierServiceDep,
) -> FeatureStubResponse:
    _ = payload, service
    return FeatureStubResponse(feature="classifier proxy")
