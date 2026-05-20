from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.api.schemas.widget import WidgetConfigUpsertRequest
from app.infra.exceptions import NotFoundError
from app.repositories.widget_repo import WidgetConfigRecord
from app.services.widget_service import WidgetService


class FakeWidgetRepository:
    def __init__(self):
        self.records = {}

    async def upsert_config(
        self,
        *,
        widget_id,
        allowed_origins,
        theme,
        greeting,
        enabled_tools,
        created_by_user_id,
    ):
        record = WidgetConfigRecord(
            id=uuid4(),
            widget_id=widget_id,
            allowed_origins=allowed_origins,
            theme=theme,
            greeting=greeting,
            enabled_tools=enabled_tools,
            created_by_user_id=created_by_user_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.records[widget_id] = record
        return record

    async def get_config(self, widget_id):
        return self.records.get(widget_id)

    async def list_configs(self, *, limit=100):
        return list(self.records.values())[:limit]


@pytest.mark.asyncio
async def test_widget_service_upserts_and_returns_public_config():
    service = WidgetService(repository=FakeWidgetRepository())
    actor_id = uuid4()

    saved = await service.upsert_config(
        payload=WidgetConfigUpsertRequest(
            widget_id="docs-helper",
            allowed_origins=["https://example.com"],
            theme={"mode": "dark", "accent_color": "#111827"},
            greeting="Ask me about pandas maintenance.",
            enabled_tools=["rag_search", "classify_issue"],
        ),
        actor_user_id=actor_id,
    )
    public = await service.get_public_config("docs-helper")

    assert saved.widget_id == "docs-helper"
    assert saved.created_by_user_id == actor_id
    assert public.enabled_tools == ["rag_search", "classify_issue"]
    assert public.greeting == "Ask me about pandas maintenance."


@pytest.mark.asyncio
async def test_widget_service_raises_for_missing_public_config():
    service = WidgetService(repository=FakeWidgetRepository())

    with pytest.raises(NotFoundError):
        await service.get_public_config("missing")
