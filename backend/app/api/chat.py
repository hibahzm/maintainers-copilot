from fastapi import APIRouter

from app.api.dependencies import ChatServiceDep
from app.api.schemas.chat import ChatRequest
from app.api.schemas.common import FeatureStubResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=FeatureStubResponse)
async def create_chat_response(
    payload: ChatRequest,
    service: ChatServiceDep,
) -> FeatureStubResponse:
    _ = payload, service
    return FeatureStubResponse(feature="streaming chat")
