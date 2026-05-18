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
- The backend API can continue using the root `pyproject.toml`; the model server and Streamlit UI now have local dependency manifests ready for later Dockerfiles.
- Dataset work will begin from raw GitHub issues, with notebook compute allowed for training but reproducibility anchored in repository scripts and committed dataset formats.
