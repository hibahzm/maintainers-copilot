from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.api.schemas.common import APIModel

WidgetToolName = Literal["rag_search", "classify_issue", "extract_entities", "summarize_issue"]


class WidgetConfigUpsertRequest(APIModel):
    widget_id: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    allowed_origins: list[str] = Field(default_factory=list, max_length=20)
    theme: dict = Field(default_factory=lambda: {"mode": "light", "accent_color": "#2563eb"})
    greeting: str = Field(default="How can I help maintainers today?", max_length=500)
    enabled_tools: list[WidgetToolName] = Field(default_factory=lambda: ["rag_search"])


class WidgetConfigResponse(APIModel):
    id: UUID
    widget_id: str
    allowed_origins: list[str]
    theme: dict
    greeting: str
    enabled_tools: list[str]
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class PublicWidgetConfigResponse(APIModel):
    widget_id: str
    theme: dict
    greeting: str
    enabled_tools: list[str]
