# Maintainers Copilot

Maintainers Copilot is a multi-service application for repository support workflows: issue classification, retrieval-augmented answers, long-term memory, a maintainer-facing chat interface, and an embeddable support widget.

## Scaffold status

This repository is currently in **Milestone 0: scaffold**. The code is intentionally thin; the goal is to make responsibilities visible before we begin implementing behavior.

## Planned services

- `backend/` — main FastAPI backend
- `model_server/` — separate inference API for classifier / NER / summarizer models
- `chatbot/` — Streamlit maintainer UI
- `widget/` — embeddable React widget
- `demo/host/` — tiny host page for widget demos
- infrastructure via Docker Compose — PostgreSQL + pgvector, Redis, MinIO, Vault

## Start here

1. Read `docs/ARCH.md` for boundaries.
2. Read `docs/BUILD_PLAN.md` for the card-by-card build path.
3. Read `docs/REPORT.md` for the running change log.

## Engineering conventions

- Python dependency management is `uv`-first.
- Every Python service gets a `pyproject.toml` beside its eventual `Dockerfile`:
  - `backend/` → backend API
  - `model_server/` → inference service
  - `chatbot/` → Streamlit UI
- PostgreSQL schema changes go through Alembic migrations from the first real table onward.
