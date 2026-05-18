# Migrations

Alembic is the required path for PostgreSQL schema changes.

The baseline belongs in the foundation milestone, with the first revision creating the initial `users`, `widgets`, `audit_log`, and `memory` tables. Every later schema change should be represented by a committed Alembic revision under `migrations/versions/`.
