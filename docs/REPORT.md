# Project Report

This is the running build journal. Every meaningful change should add a dated entry so future us can reconstruct not only what changed, but why.

## 2026-05-18 — Milestone 0: Initial scaffold

### Added
- repository-level bootstrap files: `README.md`, `.gitignore`, `.env.example`, `pyproject.toml`, `docker-compose.yml`
- main backend skeleton under `app/`
- separate inference service skeleton under `model_server/`
- Streamlit shell under `chatbot/`
- React widget shell under `widget/`
- demo host, prompts, eval placeholders, data files, migrations shell, and documentation set
- `app/core/` for configuration concerns and `tests/` so testing exists from day one

### Design notes
- Kept the user's proposed architecture nearly intact because it already separates transport, workflows, persistence, and external adapters well.
- Added `model_server/main.py` so the inference service has one obvious entrypoint.
- Kept `docker-compose.yml` honest at scaffold time: infrastructure services are defined now; app containers are added when Dockerfiles exist.

### Next intended change
- Milestone 1: make the backend boot cleanly, add settings/tests, and run the first local health check.

## 2026-05-18 — Scaffold refinement

### Added
- `model_server/pyproject.toml`
- `chatbot/pyproject.toml`
- `docs/DATASET_STRATEGY.md`

### Updated
- documented `uv` as the standard Python package manager
- recorded the rule that each Python service keeps `pyproject.toml` beside its future `Dockerfile`
- recorded Alembic as the only accepted path for PostgreSQL schema changes

### Design notes
- The backend API initially used the root `pyproject.toml`; the model server and Streamlit UI received local dependency manifests ready for later Dockerfiles.
- Dataset work will begin from raw GitHub issues, with notebook compute allowed for training but reproducibility anchored in repository scripts and committed dataset formats.

## 2026-05-18 — Dependency manifest clarification

### Updated
- removed the old `ui` and `ml` optional dependency groups from the root `pyproject.toml`

### Design notes
- Each Python container should install only from the manifest that belongs to that service:
  - `backend/pyproject.toml` → API backend
  - `model_server/pyproject.toml` → inference service
  - `chatbot/pyproject.toml` → Streamlit UI
- This keeps the API image from carrying large ML dependencies it does not need.

## 2026-05-18 — Backend service isolation

### Moved
- `app/` → `backend/app/`
- `tests/` → `backend/tests/`
- root `pyproject.toml` → `backend/pyproject.toml`

### Design notes
- The repo root is now orchestration-level only; each Python container has its own explicit service folder and colocated manifest.
- This is more legible than treating the repository root as an implicit backend service.

## 2026-05-18 — API contracts and dependency wiring

### Added
- `backend/app/api/schemas/` for Pydantic request/response models
- `backend/app/api/dependencies.py` for FastAPI dependency providers
- `backend/app/services/auth_service.py`
- `backend/app/services/widget_service.py`

### Updated
- routers now accept typed Pydantic payloads and injected service dependencies
- existing service placeholders are explicit classes, not loose module docstrings

### Design notes
- `api/schemas` are public HTTP contracts; `domain` models remain internal business concepts.
- Routers should depend on services, never instantiate infrastructure or repositories directly.

## 2026-05-18 — Week 7 dataset locked

### Updated
- `docs/DATASET_STRATEGY.md`
- `docs/BUILD_PLAN.md`
- `docs/DECISIONS.md`
- `data/README.md`

### Design notes
- Week 7 uses **closed issues from `fastapi/fastapi` only**.
- Dataset scripts should default to that repository so later work does not drift back into a multi-repo strategy.
- Before training, we should inspect class balance across the target labels and document any sampling choice.

## 2026-05-18 — Plan aligned to the project brief

### Updated
- rewrote `docs/BUILD_PLAN.md` around five dependency-ordered milestones from the brief
- expanded `docs/ARCH.md` with the full compose stack and delivery order
- clarified Colab usage in `docs/DATASET_STRATEGY.md`
- moved Alembic baseline work into the foundation milestone

### Design notes
- The brief expects foundations before feature work: full stack shape, Vault, tracing, Alembic baseline, dataset fetch/splits, then the first training run.
- Colab is appropriate for GPU-heavy experiments, especially classifier fine-tuning, but repository code remains the durable source of truth.

## 2026-05-18 — Foundation stack started

### Added
- Dockerfiles for `backend/`, `model_server/`, `chatbot/`, `widget/`, `demo/host/`, and the new `migrate/` service
- `migrate/pyproject.toml`, `migrate/entrypoint.sh`, and `migrate/README.md`
- root `.dockerignore`
- widget Nginx config

### Updated
- expanded `docker-compose.yml` to the full ten-service stack from the brief
- added service health checks and dependency ordering
- added `WIDGET_PORT` to `.env.example`

### Design notes
- Python service images use `uv` and keep the manifest beside their Dockerfile.
- `migrate` is present now as a one-shot service scaffold; the next foundation pass will replace the placeholder behavior with the actual Alembic baseline.
- The compose dependency graph now makes the intended boot order explicit: infra first, migrations before API, API before user-facing surfaces.
