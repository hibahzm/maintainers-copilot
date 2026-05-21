from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.api.schemas.widget import WidgetConfigUpsertRequest
from app.infra.exceptions import NotFoundError, PermissionDenied
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
    public = await service.get_public_config(
        "docs-helper",
        request_origin="https://example.com",
    )

    assert saved.widget_id == "docs-helper"
    assert saved.created_by_user_id == actor_id
    assert public.enabled_tools == ["rag_search", "classify_issue"]
    assert public.greeting == "Ask me about pandas maintenance."


@pytest.mark.asyncio
async def test_widget_service_raises_for_missing_public_config():
    service = WidgetService(repository=FakeWidgetRepository())

    with pytest.raises(NotFoundError):
        await service.get_public_config("missing", request_origin="https://example.com")


@pytest.mark.asyncio
async def test_widget_service_rejects_disallowed_origin():
    service = WidgetService(repository=FakeWidgetRepository())

    await service.upsert_config(
        payload=WidgetConfigUpsertRequest(
            widget_id="docs-helper",
            allowed_origins=["https://allowed.example"],
            theme={"mode": "light"},
            greeting="Hello",
            enabled_tools=["rag_search"],
        ),
        actor_user_id=uuid4(),
    )

    with pytest.raises(PermissionDenied):
        await service.get_public_config(
            "docs-helper",
            request_origin="https://blocked.example",
        )


def test_widget_loader_passes_host_origin_to_iframe():
    service = WidgetService(repository=FakeWidgetRepository())

    script = service.loader_script(widget_public_url="http://localhost:4173")

    assert "hostOrigin = window.location.origin" in script
    assert "/widget/frame/${encodeURIComponent(widgetId)}" in script
    assert 'frameUrl.searchParams.set("hostOrigin", hostOrigin)' in script


@pytest.mark.asyncio
async def test_widget_frame_uses_allowed_origins_for_csp():
    service = WidgetService(repository=FakeWidgetRepository())

    await service.upsert_config(
        payload=WidgetConfigUpsertRequest(
            widget_id="docs-helper",
            allowed_origins=["https://allowed.example"],
            theme={"mode": "light"},
            greeting="Hello",
            enabled_tools=["rag_search"],
        ),
        actor_user_id=uuid4(),
    )

    html, frame_ancestors = await service.get_frame_html(
        "docs-helper",
        request_origin="https://allowed.example",
        widget_public_url="http://localhost:4173",
        api_base="http://localhost:8000",
        host_origin="https://allowed.example",
    )

    assert "http://localhost:4173/" in html
    assert "hostOrigin=https%3A//allowed.example" in html
    assert frame_ancestors == "frame-ancestors https://allowed.example"
