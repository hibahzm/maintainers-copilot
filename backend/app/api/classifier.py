from fastapi import APIRouter

from app.api.dependencies import ClassifierServiceDep
from app.api.schemas.classifier import ClassifyIssueRequest, ClassifyIssueResponse

router = APIRouter(prefix="/classifier", tags=["classifier"])


@router.post("", response_model=ClassifyIssueResponse)
async def classify_issue(
    payload: ClassifyIssueRequest,
    service: ClassifierServiceDep,
) -> ClassifyIssueResponse:
    return await service.classify_issue(title=payload.title, body=payload.body)
