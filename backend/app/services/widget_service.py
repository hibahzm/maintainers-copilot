"""Widget configuration and embed-snippet workflows."""

from uuid import UUID

from app.api.schemas.widget import (
    PublicWidgetConfigResponse,
    WidgetConfigResponse,
    WidgetConfigUpsertRequest,
)
from app.infra.exceptions import NotFoundError
from app.repositories.widget_repo import WidgetConfigRecord, WidgetRepository


class WidgetService:
    """Manage public widget config and admin-owned configuration changes."""

    def __init__(self, *, repository: WidgetRepository) -> None:
        self.repository = repository

    async def upsert_config(
        self,
        *,
        payload: WidgetConfigUpsertRequest,
        actor_user_id: UUID,
    ) -> WidgetConfigResponse:
        record = await self.repository.upsert_config(
            widget_id=payload.widget_id,
            allowed_origins=payload.allowed_origins,
            theme=payload.theme,
            greeting=payload.greeting,
            enabled_tools=list(payload.enabled_tools),
            created_by_user_id=actor_user_id,
        )
        return self._response(record)

    async def get_public_config(self, widget_id: str) -> PublicWidgetConfigResponse:
        record = await self.repository.get_config(widget_id)
        if record is None:
            raise NotFoundError("Widget config not found.")
        return PublicWidgetConfigResponse(
            widget_id=record.widget_id,
            theme=record.theme,
            greeting=record.greeting,
            enabled_tools=record.enabled_tools,
        )

    async def list_configs(self, *, limit: int = 100) -> list[WidgetConfigResponse]:
        records = await self.repository.list_configs(limit=limit)
        return [self._response(record) for record in records]

    def _response(self, record: WidgetConfigRecord) -> WidgetConfigResponse:
        return WidgetConfigResponse.model_validate(record.model_dump())
