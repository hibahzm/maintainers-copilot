"""Widget configuration persistence queries."""

import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import asyncpg
from pydantic import BaseModel


class WidgetConfigRecord(BaseModel):
    id: UUID
    widget_id: str
    allowed_origins: list[str]
    theme: dict[str, Any]
    greeting: str
    enabled_tools: list[str]
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class WidgetRepository:
    def __init__(self, *, database_url: str) -> None:
        self.database_url = database_url

    async def upsert_config(
        self,
        *,
        widget_id: str,
        allowed_origins: list[str],
        theme: dict,
        greeting: str,
        enabled_tools: list[str],
        created_by_user_id: UUID,
    ) -> WidgetConfigRecord:
        conn = await asyncpg.connect(self.database_url)
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO widgets (
                    id,
                    widget_id,
                    allowed_origins,
                    theme,
                    greeting,
                    enabled_tools,
                    created_by_user_id
                )
                VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7)
                ON CONFLICT (widget_id) DO UPDATE SET
                    allowed_origins = EXCLUDED.allowed_origins,
                    theme = EXCLUDED.theme,
                    greeting = EXCLUDED.greeting,
                    enabled_tools = EXCLUDED.enabled_tools,
                    updated_at = now()
                RETURNING
                    id,
                    widget_id,
                    allowed_origins,
                    theme,
                    greeting,
                    enabled_tools,
                    created_by_user_id,
                    created_at,
                    updated_at
                """,
                uuid4(),
                widget_id,
                allowed_origins,
                json.dumps(theme),
                greeting,
                enabled_tools,
                created_by_user_id,
            )
            await conn.execute(
                """
                INSERT INTO audit_log (id, actor_user_id, action, target_type, target_id, metadata)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                """,
                uuid4(),
                created_by_user_id,
                "widget.config.upsert",
                "widget",
                widget_id,
                json.dumps(
                    {
                        "allowed_origins_count": len(allowed_origins),
                        "enabled_tools": enabled_tools,
                    }
                ),
            )
        finally:
            await conn.close()

        if row is None:
            raise RuntimeError("Widget config upsert did not return a row.")
        return self._record(row)

    async def get_config(self, widget_id: str) -> WidgetConfigRecord | None:
        conn = await asyncpg.connect(self.database_url)
        try:
            row = await conn.fetchrow(
                """
                SELECT
                    id,
                    widget_id,
                    allowed_origins,
                    theme,
                    greeting,
                    enabled_tools,
                    created_by_user_id,
                    created_at,
                    updated_at
                FROM widgets
                WHERE widget_id = $1
                """,
                widget_id,
            )
        finally:
            await conn.close()
        return self._record(row) if row else None

    async def list_configs(self, *, limit: int = 100) -> list[WidgetConfigRecord]:
        conn = await asyncpg.connect(self.database_url)
        try:
            rows = await conn.fetch(
                """
                SELECT
                    id,
                    widget_id,
                    allowed_origins,
                    theme,
                    greeting,
                    enabled_tools,
                    created_by_user_id,
                    created_at,
                    updated_at
                FROM widgets
                ORDER BY updated_at DESC, created_at DESC
                LIMIT $1
                """,
                limit,
            )
        finally:
            await conn.close()
        return [self._record(row) for row in rows]

    def _record(self, row: asyncpg.Record) -> WidgetConfigRecord:
        data = dict(row)
        if isinstance(data.get("theme"), str):
            data["theme"] = json.loads(data["theme"])
        return WidgetConfigRecord.model_validate(data)
