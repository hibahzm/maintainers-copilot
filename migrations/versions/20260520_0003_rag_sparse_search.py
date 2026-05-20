"""add sparse search index for rag chunks

Revision ID: 20260520_0003
Revises: 20260520_0002
Create Date: 2026-05-20
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260520_0003"
down_revision: str | None = "20260520_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE rag_chunks
        ADD COLUMN search_vector tsvector GENERATED ALWAYS AS (
            to_tsvector(
                'english',
                coalesce(title, '') || ' ' ||
                coalesce(parent_title, '') || ' ' ||
                coalesce(text, '')
            )
        ) STORED
        """
    )
    op.execute("CREATE INDEX ix_rag_chunks_search_vector ON rag_chunks USING gin (search_vector)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_rag_chunks_search_vector")
    op.execute("ALTER TABLE rag_chunks DROP COLUMN IF EXISTS search_vector")
