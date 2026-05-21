from fastapi import APIRouter

from app.api.dependencies import RagServiceDep
from app.api.schemas.rag import RagQueryRequest, RagQueryResponse

router = APIRouter(prefix="/rag", tags=["rag"])


@router.get("/status")
async def rag_status(service: RagServiceDep) -> dict:
    return await service.status()


@router.post("/query", response_model=RagQueryResponse)
async def query_rag(
    payload: RagQueryRequest,
    service: RagServiceDep,
) -> RagQueryResponse:
    return await service.query(
        question=payload.question,
        top_k=payload.top_k,
        source_type=payload.source_type,
        generate_answer=payload.generate_answer,
    )
