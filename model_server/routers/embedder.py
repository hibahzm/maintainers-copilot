"""FastAPI router for text embeddings."""

from fastapi import APIRouter, HTTPException, status

from model_server.schemas.embedder import EmbedTextRequest, EmbedTextResponse
from model_server.services.embedder import get_embedder

router = APIRouter(tags=["embeddings"])


@router.post("/embed", response_model=EmbedTextResponse)
async def embed_text(payload: EmbedTextRequest) -> EmbedTextResponse:
    try:
        return get_embedder().embed(texts=payload.texts, input_type=payload.input_type)
    except Exception as exc:  # noqa: BLE001 - keep model internals behind API boundary
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding inference failed.",
        ) from exc
