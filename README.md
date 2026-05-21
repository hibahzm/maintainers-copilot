# Maintainers Copilot

Maintainers Copilot is a multi-service application for repository support workflows: issue classification, retrieval-augmented answers, long-term memory, a maintainer-facing chat interface, and an embeddable support widget.

## Current status

This repository is currently in **Step 1: build the foundation**. The structure is in place, and we are now turning it into a bootable stack with Compose, Vault, tracing, migrations, and the dataset pipeline.

## Planned services

- `backend/` — main FastAPI backend
- `model_server/` — separate inference API for classifier / NER / summarizer models
- `chatbot/` — Streamlit maintainer UI
- `migrate/` — one-shot Alembic migration runner
- `widget/` — embeddable React widget
- `demo/host/` — tiny host page for widget demos
- infrastructure via Docker Compose — PostgreSQL + pgvector, Redis, MinIO, Vault

## Start here

1. Read `docs/ARCH.md` for boundaries.
2. Read `docs/DECISIONS.md` for accepted model, RAG, tracing, and architecture decisions.
3. Read `docs/RUNBOOK.md` for local startup and demo operations.
4. Read `docs/EVALS.md` for evaluation suites and evidence files.
5. Read `docs/SECURITY.md` for secrets, redaction, auth, and widget safety notes.
6. Read `docs/BUILD_PLAN.md` for the card-by-card build path.
7. Read `docs/REPORT.md` for the running change log.
8. Open `notebooks/maintainers_copilot_week7_colab.ipynb` in Colab for the standalone notebook workflow.

## Engineering conventions

- Python dependency management is `uv`-first.
- Every Python service gets a `pyproject.toml` beside its eventual `Dockerfile`:
  - `backend/` → backend API
  - `model_server/` → inference service
  - `chatbot/` → Streamlit UI
  - `migrate/` → Alembic migration runner
- PostgreSQL schema changes go through Alembic migrations from the first real table onward.
