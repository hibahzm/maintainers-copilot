"""FastAPI router for RAG answer generation."""

from fastapi import APIRouter, HTTPException, status

from model_server.schemas.rag_answer import RagAnswerRequest, RagAnswerResponse
from model_server.services.rag_answer import get_rag_answerer
from model_server.services.summarizer import OpenAIKeyMissingError

router = APIRouter(tags=["rag-answer"])


@router.post("/rag-answer", response_model=RagAnswerResponse)
async def rag_answer(payload: RagAnswerRequest) -> RagAnswerResponse:
    try:
        return get_rag_answerer().answer(payload)
    except OpenAIKeyMissingError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - keep LLM internals behind API boundary
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RAG answer generation failed.",
        ) from exc
