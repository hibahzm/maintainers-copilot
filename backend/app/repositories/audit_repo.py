"""Audit-log persistence queries live here."""

import json
from uuid import UUID, uuid4

import asyncpg


class AuditRepository:
    def __init__(self, *, database_url: str) -> None:
        self.database_url = database_url

    async def record(
        self,
        *,
        actor_user_id: UUID,
        action: str,
        target_type: str,
        target_id: str,
        metadata: dict,
    ) -> None:
        conn = await asyncpg.connect(self.database_url)
        try:
            await conn.execute(
                """
                INSERT INTO audit_log (id, actor_user_id, action, target_type, target_id, metadata)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                """,
                uuid4(),
                actor_user_id,
                action,
                target_type,
                target_id,
                json.dumps(metadata),
            )
        finally:
            await conn.close()
