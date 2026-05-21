"""Development bootstrap records for the local Docker stack."""

from __future__ import annotations

import json
from uuid import UUID, uuid4

import asyncpg

from app.core.config import Settings
from app.infra.tracing import trace_event
from app.services.auth_service import hash_password

_DEFAULT_WIDGET_ORIGINS = [
    "http://localhost:8501",
    "http://127.0.0.1:8501",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

_DEFAULT_WIDGET_THEME = {
    "mode": "light",
    "accent_color": "#0891b2",
}

_DEFAULT_WIDGET_TOOLS = [
    "rag_search",
    "classify_issue",
    "extract_entities",
]


async def bootstrap_dev_data(settings: Settings) -> None:
    """Create a predictable admin and widget config for local Compose runs.

    The bootstrap is intentionally narrow: it only touches the configured dev
    admin email and only adds required local origins to an existing widget,
    so admin edits to greeting, theme, and tools are preserved across restarts.
    """

    if not settings.bootstrap_dev_data:
        return

    password = settings.dev_admin_password.get_secret_value()
    if len(password) < 8:
        trace_event("bootstrap.skipped", reason="dev_admin_password_too_short")
        return

    conn = await asyncpg.connect(settings.database_url)
    try:
        admin_id = await _ensure_admin_user(
            conn,
            email=settings.dev_admin_email,
            password=password,
        )
        await _ensure_default_widget(
            conn,
            widget_id=settings.default_widget_id,
            created_by_user_id=admin_id,
        )
    finally:
        await conn.close()


async def _ensure_admin_user(
    conn: asyncpg.Connection,
    *,
    email: str,
    password: str,
) -> UUID:
    row = await conn.fetchrow(
        """
        INSERT INTO users (id, email, hashed_password, role, is_active)
        VALUES ($1, $2, $3, 'admin', true)
        ON CONFLICT (email) DO UPDATE SET
            hashed_password = EXCLUDED.hashed_password,
            role = 'admin',
            is_active = true
        RETURNING id
        """,
        uuid4(),
        email.strip().lower(),
        hash_password(password),
    )
    if row is None:
        raise RuntimeError("Admin bootstrap did not return a user id.")
    trace_event("bootstrap.admin.ready", email=email)
    return row["id"]


async def _ensure_default_widget(
    conn: asyncpg.Connection,
    *,
    widget_id: str,
    created_by_user_id: UUID,
) -> None:
    await conn.execute(
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
            allowed_origins = (
                SELECT array_agg(DISTINCT origin)
                FROM unnest(widgets.allowed_origins || EXCLUDED.allowed_origins) AS merged(origin)
            ),
            updated_at = now()
        """,
        uuid4(),
        widget_id,
        _DEFAULT_WIDGET_ORIGINS,
        json.dumps(_DEFAULT_WIDGET_THEME),
        "Ask about triage, project context, or an issue you are trying to route.",
        _DEFAULT_WIDGET_TOOLS,
        created_by_user_id,
    )
    trace_event("bootstrap.widget.ready", widget_id=widget_id)
