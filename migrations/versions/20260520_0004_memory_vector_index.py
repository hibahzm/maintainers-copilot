"""constrain and index long-term memory embeddings

Revision ID: 20260520_0004
Revises: 20260520_0003
Create Date: 2026-05-20
"""

from collections.abc import Sequence

from alembic import op
from pgvector.sqlalchemy import VECTOR


revision: str = "20260520_0004"
down_revision: str | None = "20260520_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "memory",
        "embedding",
        existing_type=VECTOR(),
        type_=VECTOR(384),
        existing_nullable=True,
    )
    op.create_index(
        "ix_memory_embedding_hnsw",
        "memory",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index("ix_memory_memory_type", "memory", ["memory_type"])


def downgrade() -> None:
    op.drop_index("ix_memory_memory_type", table_name="memory")
    op.drop_index("ix_memory_embedding_hnsw", table_name="memory")
    op.alter_column(
        "memory",
        "embedding",
        existing_type=VECTOR(384),
        type_=VECTOR(),
        existing_nullable=True,
    )
