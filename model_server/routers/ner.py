"""FastAPI router for named-entity extraction."""

from fastapi import APIRouter

from model_server.schemas.ner import NERRequest, NERResponse
from model_server.services.ner import extract_entities

router = APIRouter(tags=["ner"])


@router.post("/ner", response_model=NERResponse)
async def extract_entities_endpoint(payload: NERRequest) -> NERResponse:
    return extract_entities(payload)
