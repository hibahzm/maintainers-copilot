"""Pydantic contracts for named-entity extraction."""

from pydantic import BaseModel


class NERResponse(BaseModel):
    status: str
    feature: str
