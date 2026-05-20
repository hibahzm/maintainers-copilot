"""create rag pgvector tables

Revision ID: 20260520_0002
Revises: 20260518_0001
Create Date: 2026-05-20
"""

from collections.abc import Sequence

from alembic import op
from pgvector.sqlalchemy import VECTOR
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260520_0002"
down_revision: str | None = "20260518_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIMENSIONS = 384


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "rag_sources",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "rag_chunks",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("parent_id", sa.Text(), nullable=True),
        sa.Column("chunk_strategy", sa.String(length=64), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("parent_title", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("start_char", sa.Integer(), nullable=True),
        sa.Column("end_char", sa.Integer(), nullable=True),
        sa.Column("start_word", sa.Integer(), nullable=True),
        sa.Column("end_word", sa.Integer(), nullable=True),
        sa.Column("embedding", VECTOR(EMBEDDING_DIMENSIONS), nullable=True),
        sa.Column("embedding_model", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["source_id"], ["rag_sources.id"], name="fk_rag_chunks_source_id", ondelete="CASCADE"),
    )

    op.create_index("ix_rag_sources_source_type", "rag_sources", ["source_type"])
    op.create_index("ix_rag_sources_metadata", "rag_sources", ["metadata"], postgresql_using="gin")
    op.create_index("ix_rag_chunks_source_id", "rag_chunks", ["source_id"])
    op.create_index("ix_rag_chunks_chunk_strategy", "rag_chunks", ["chunk_strategy"])
    op.create_index("ix_rag_chunks_embedding_model", "rag_chunks", ["embedding_model"])
    op.create_index("ix_rag_chunks_metadata", "rag_chunks", ["metadata"], postgresql_using="gin")
    op.execute(
        "CREATE INDEX ix_rag_chunks_embedding_hnsw "
        "ON rag_chunks USING hnsw (embedding vector_cosine_ops) "
        "WHERE embedding IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_rag_chunks_embedding_hnsw")
    op.drop_index("ix_rag_chunks_metadata", table_name="rag_chunks")
    op.drop_index("ix_rag_chunks_embedding_model", table_name="rag_chunks")
    op.drop_index("ix_rag_chunks_chunk_strategy", table_name="rag_chunks")
    op.drop_index("ix_rag_chunks_source_id", table_name="rag_chunks")
    op.drop_index("ix_rag_sources_metadata", table_name="rag_sources")
    op.drop_index("ix_rag_sources_source_type", table_name="rag_sources")
    op.drop_table("rag_chunks")
    op.drop_table("rag_sources")
