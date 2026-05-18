from pydantic import Field

from app.api.schemas.common import APIModel


class RagQueryRequest(APIModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class RagQueryResponse(APIModel):
    answer: str
    citations: list[str]
