from fastapi import APIRouter

from app.api.dependencies import RagServiceDep
from app.api.schemas.common import FeatureStubResponse
from app.api.schemas.rag import RagQueryRequest

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/query", response_model=FeatureStubResponse)
async def query_rag(
    payload: RagQueryRequest,
    service: RagServiceDep,
) -> FeatureStubResponse:
    _ = payload, service
    return FeatureStubResponse(feature="rag query")
