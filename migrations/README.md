# Migrations

Alembic is the required path for PostgreSQL schema changes.

Configuration will be introduced when the first persistent schema lands, and every later schema change should be represented by a committed Alembic revision under `migrations/versions/`.
