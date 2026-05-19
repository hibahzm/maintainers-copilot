from pydantic import Field

from app.api.schemas.common import APIModel
from app.domain.issue import ClassificationLabel


class ClassifyIssueRequest(APIModel):
    title: str = Field(min_length=1, max_length=300)
    body: str = ""


class ClassifyIssueResponse(APIModel):
    label: ClassificationLabel
    confidence: float = Field(ge=0.0, le=1.0)
    scores: dict[ClassificationLabel, float] = Field(default_factory=dict)
    model_name: str | None = None
    model_dir: str | None = None
