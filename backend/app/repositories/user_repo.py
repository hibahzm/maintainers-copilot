"""User persistence queries."""

from datetime import datetime
from uuid import UUID, uuid4

import asyncpg
from pydantic import BaseModel


class UserRecord(BaseModel):
    id: UUID
    email: str
    hashed_password: str
    role: str
    is_active: bool
    created_at: datetime


class DuplicateUserError(RuntimeError):
    """Raised when an email is already registered."""


class UserRepository:
    def __init__(self, *, database_url: str) -> None:
        self.database_url = database_url

    async def create_user(
        self,
        *,
        email: str,
        hashed_password: str,
        role: str = "user",
    ) -> UserRecord:
        conn = await asyncpg.connect(self.database_url)
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO users (id, email, hashed_password, role)
                VALUES ($1, $2, $3, $4)
                RETURNING id, email, hashed_password, role, is_active, created_at
                """,
                uuid4(),
                email,
                hashed_password,
                role,
            )
        except asyncpg.UniqueViolationError as exc:
            raise DuplicateUserError("A user with this email already exists.") from exc
        finally:
            await conn.close()

        if row is None:
            raise RuntimeError("User insert did not return a row.")
        return UserRecord.model_validate(dict(row))

    async def get_user_by_email(self, email: str) -> UserRecord | None:
        row = await self._fetch_user("email = $1", email)
        return UserRecord.model_validate(dict(row)) if row else None

    async def get_user_by_id(self, user_id: UUID) -> UserRecord | None:
        row = await self._fetch_user("id = $1", user_id)
        return UserRecord.model_validate(dict(row)) if row else None

    async def update_role(self, *, user_id: UUID, role: str) -> UserRecord | None:
        conn = await asyncpg.connect(self.database_url)
        try:
            row = await conn.fetchrow(
                """
                UPDATE users
                SET role = $2
                WHERE id = $1
                RETURNING id, email, hashed_password, role, is_active, created_at
                """,
                user_id,
                role,
            )
        finally:
            await conn.close()
        return UserRecord.model_validate(dict(row)) if row else None

    async def _fetch_user(self, predicate: str, value) -> asyncpg.Record | None:
        conn = await asyncpg.connect(self.database_url)
        try:
            return await conn.fetchrow(
                f"""
                SELECT id, email, hashed_password, role, is_active, created_at
                FROM users
                WHERE {predicate}
                """,
                value,
            )
        finally:
            await conn.close()
