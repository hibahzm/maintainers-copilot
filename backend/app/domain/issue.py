from enum import StrEnum

from pydantic import BaseModel


class ClassificationLabel(StrEnum):
    bug = "bug"
    feature = "feature"
    docs = "docs"
    question = "question"


class IssueEntity(BaseModel):
    id: str
    title: str
    body: str
    labels: list[str] = []
