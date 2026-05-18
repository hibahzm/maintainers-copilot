# Migrations

Alembic is the required path for PostgreSQL schema changes.

The foundation baseline now exists:

- `alembic.ini`
- `migrations/env.py`
- `migrations/script.py.mako`
- `migrations/versions/20260518_0001_foundation_tables.py`

The first revision creates the initial `users`, `widgets`, `audit_log`, and `memory` tables. Every later schema change should be represented by a committed Alembic revision under `migrations/versions/`.

`memory.embedding` starts as an unconstrained pgvector `VECTOR` column because the embedding-model choice is intentionally made later during the RAG work. Once that choice is backed by retrieval numbers, we can add the dimension constraint/indexes in a later migration instead of freezing the wrong dimension too early.
