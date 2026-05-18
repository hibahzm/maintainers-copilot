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
- Week 7 uses **closed issues from `pandas-dev/pandas` only**.
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

## 2026-05-18 — Alembic baseline added

### Added
- root `alembic.ini`
- `migrations/env.py`
- `migrations/script.py.mako`
- first revision: `migrations/versions/20260518_0001_foundation_tables.py`

### Updated
- the `migrate` image now copies `alembic.ini`
- the migrate entrypoint now always runs `alembic upgrade head`

### Design notes
- The first revision creates the foundation tables required by the brief: `users`, `widgets`, `audit_log`, and `memory`.
- From here forward, PostgreSQL shape changes have a real migration lineage rather than only a reserved folder.
- `memory.embedding` uses pgvector's unconstrained `VECTOR` type for now; we will pin dimensions later once the embedding model is chosen with retrieval evidence.

## 2026-05-18 — Colab handoff clarified

### Updated
- `docs/BUILD_PLAN.md`
- `docs/DATASET_STRATEGY.md`
- `docs/DECISIONS.md`

### Design notes
- When the training step arrives, the user will run the notebook online in Google Colab.
- We will prepare the Colab-ready code at that point, after the dataset pipeline is defined, instead of creating notebooks prematurely.

## 2026-05-18 — Label vocabulary normalized

### Updated
- `backend/app/domain/issue.py`
- `docs/DATASET_STRATEGY.md`
- `docs/DECISIONS.md`

### Design notes
- Standardized the classifier target vocabulary to the assignment wording: `bug / feature / docs / question`.
- Removed the parallel `documentation` target so code, docs, future splits, and evals converge on one canonical label name.

## 2026-05-18 — Vault startup boundary added

### Added
- startup-time Vault client logic in `backend/app/infra/vault.py`
- explicit runtime secret schema in `backend/app/core/config.py`

### Updated
- API lifespan startup in `backend/app/main.py`
- `docs/SECURITY.md`
- `docs/RUNBOOK.md`

### Design notes
- The API now has a real code path for refusing to boot when Vault is unreachable or required secrets are missing.
- Runtime secrets are modeled explicitly so later auth, storage, LLM, and tracing work can consume one validated secret bundle instead of reading ad hoc environment variables.

## 2026-05-18 — Request tracing spine added

### Added
- request/trace context helpers in `backend/app/infra/tracing.py`
- middleware that binds and echoes `X-Request-ID` plus `X-Trace-ID`

### Updated
- API app wiring in `backend/app/main.py`
- trace settings in `backend/app/core/config.py`
- tracing decision in `docs/DECISIONS.md`
- `docs/RUNBOOK.md`

### Design notes
- Chose Langfuse as the eventual trace UI because this project needs conversation trees with LLM/tool/retrieval detail more than a generic HTTP dashboard.
- Kept provider-independent request/trace IDs in our own infra layer so later structured logs, errors, and Langfuse spans can join cleanly without leaking vendor concerns through the app.

## 2026-05-18 — Dataset pipeline coded

### Added
- `scripts/dataset/` package with source constants, JSONL helpers, GitHub issue fetching, and split building

### Updated
- `data/README.md`
- `docs/DATASET_STRATEGY.md`
- `docs/DECISIONS.md`

### Design notes
- Locked the raw source to closed issues from `pandas-dev/pandas` and mapped pandas labels into the assignment vocabulary `bug / feature / docs / question`.
- The splitter preserves chronological order, searches for low-drift temporal cutoffs, rejects splits missing any target label, and writes a machine-readable split report so later training is anchored to evidence rather than a manual shuffle.

## 2026-05-18 — First fine-tuning scaffold added

### Added
- reproducible training settings in `model_server/classifier/training_config.py`
- real training entrypoint in `model_server/classifier/train.py`
- optional `train` dependencies for the model server

### Updated
- `model_server/classifier/model_card.md`
- `docs/DECISIONS.md`

### Design notes
- The first run is defined as DistilBERT sequence classification over the assignment's four labels, with the lower four encoder blocks frozen for the initial experiment.
- The training command fingerprints the exact train/validation splits, writes a run manifest before training, logs the run to Weights & Biases, and saves final metrics beside the model artifact so the future model card can be reconstructed from evidence rather than memory.

## 2026-05-18 — Colab notebook workflow documented

### Added
- `docs/COLAB_TRAINING.md`

### Updated
- `README.md`
- `docs/DATASET_STRATEGY.md`
- `docs/RUNBOOK.md`

### Design notes
- The Colab instructions intentionally call the repository's actual fetch, split, and training modules instead of duplicating pipeline logic in notebook cells.
- This allows the user to avoid storing raw data and artifacts locally while preserving the architecture boundary: Colab is the execution surface, the repository remains the source of truth.

## 2026-05-18 — Standalone Colab notebook added

### Added
- `notebooks/maintainers_copilot_week7_colab.ipynb`

### Updated
- `README.md`
- `docs/COLAB_TRAINING.md`

### Design notes
- The notebook embeds the same fetch, normalization, split, and first-training logic so the user can upload one `.ipynb` file directly to Colab without cloning the repository there.
- This is a convenience surface, not a new architecture: future changes to the canonical repo pipeline should be reflected in the notebook to prevent drift.

## 2026-05-18 — GitHub pagination hardened

### Updated
- `scripts/dataset/fetch_issues.py`
- `notebooks/maintainers_copilot_week7_colab.ipynb`

### Design notes
- Replaced page-number guessing with GitHub `Link`-header pagination so fetching stops when the API stops advertising a next page.
- Expanded the GitHub error message to include the response body, making future API failures diagnosable from the notebook instead of collapsing into an opaque status code.

## 2026-05-18 — Validation split policy corrected

### Updated
- `scripts/dataset/build_splits.py`
- `notebooks/maintainers_copilot_week7_colab.ipynb`
- `docs/DATASET_STRATEGY.md`
- `docs/DECISIONS.md`

### Design notes
- Kept the test split as the required strictly newer temporal holdout, but changed validation to a deterministic stratified sample inside the older train/validation pool.
- This preserves future-like testing while avoiding an impossible validation split when a sparse label is not represented in every chronological window.

## 2026-05-18 — Colab run reconciled back into the repo

### Updated
- dataset source from `fastapi/fastapi` to `pandas-dev/pandas`
- pandas-specific label mapping in the dataset constants and docs
- standalone Colab notebook template
- `.gitignore`
- `docs/SECURITY.md`

### Design notes
- Adopted the useful notebook discovery that `pandas-dev/pandas` is the better dataset source, but corrected the label map to `bug → bug`, `enhancement → feature`, `docs → docs`, and `usage question → question`.
- Restored the assignment-required split policy after the notebook temporarily drifted into fully random splits.
- Removed a hardcoded GitHub token from the notebook template and documented that notebook credentials must come from runtime secrets, not saved cells.
- Ignored local `artifacts/` outputs so large training weights do not accidentally enter Git before the later MinIO handoff exists.

## 2026-05-18 — Temporal holdout sizing corrected

### Updated
- `scripts/dataset/build_splits.py`
- `notebooks/maintainers_copilot_week7_colab.ipynb`
- `docs/DATASET_STRATEGY.md`
- `docs/DECISIONS.md`

### Design notes
- The first corrected four-class split exposed a pathological 20-row test set because the old search optimized size error and label-distribution drift with equal weight.
- The temporal splitter now prioritizes the requested holdout size first and uses distribution drift only as a tie-breaker, preserving a meaningful future-like test set instead of rewarding a tiny balanced slice.
