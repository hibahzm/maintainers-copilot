from enum import StrEnum

from pydantic import BaseModel


class ClassificationLabel(StrEnum):
    bug = "bug"
    feature = "feature"
    question = "question"
    documentation = "documentation"


class IssueEntity(BaseModel):
    id: str
    title: str
    body: str
    labels: list[str] = []
