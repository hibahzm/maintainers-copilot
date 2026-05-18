# Build Plan

Think of this as our project board. We will move one card at a time from scaffold to a working Docker image.

## Board

| Card | Status | Outcome |
| --- | --- | --- |
| 0. Scaffold the repo | done | everyone can see the system shape |
| 1. Boot the backend | next | local API starts and tests pass |
| 2. Wire infrastructure + secrets | backlog | app can reach Vault, Postgres, Redis, MinIO |
| 3. Build auth + users | backlog | maintainers can register and log in |
| 4. Build classifier baseline | backlog | issues can be labeled through the model server |
| 5. Build RAG pipeline | backlog | questions retrieve grounded answers |
| 6. Build memory layer | backlog | useful long-term facts persist safely |
| 7. Build chat orchestration | backlog | chat can call tools and stream responses |
| 8. Build maintainer UI | backlog | Streamlit exposes the main workflows |
| 9. Build embeddable widget | backlog | external sites can host the chat widget |
| 10. Add evals, tracing, and security checks | backlog | quality is measurable and observable |
| 11. Dockerize the full stack | backlog | one command builds and runs the system |

---

## Card 0 — Scaffold the repo ✅

**Goal**: make the architecture visible before implementation begins.

**Files created**
- root bootstrap: `README.md`, `.gitignore`, `.env.example`, `pyproject.toml`, `docker-compose.yml`
- backend: `app/**`
- inference server: `model_server/**`
- UIs: `chatbot/**`, `widget/**`, `demo/host/**`
- support files: `prompts/**`, `evals/**`, `data/**`, `migrations/**`, `docs/**`, `tests/**`

**Done when**
- every future subsystem has a home
- the code boundaries are written down
- we have a report log and a path forward

---

## Card 1 — Boot the backend

**Goal**: run the first real FastAPI process locally.

**Create / edit**
- `app/main.py` — register routers, lifecycle, `/health`
- `app/core/config.py` — environment-backed settings
- `tests/api/test_health.py` — first smoke test
- `README.md` — local run commands

**Done when**
- `uvicorn app.main:app --reload` starts
- `GET /health` returns `200`
- first automated test passes

---

## Card 2 — Wire infrastructure + secrets

**Goal**: connect the backend to its outside world without leaking secrets into app code.

**Create / edit**
- `app/infra/vault.py` — Vault client and startup health check
- `app/infra/redis_client.py` — Redis pool and TTL helpers
- `app/infra/minio.py` — blob adapter
- `migrations/` — Alembic bootstrap; every PostgreSQL schema change after this point lands as a revision
- `docker-compose.yml` — verify infra services and persistent volumes
- `docs/RUNBOOK.md`, `docs/SECURITY.md` — startup and secret rules

**Done when**
- app refuses to boot if Vault is unavailable
- infra containers start with one command
- health checks prove every dependency is reachable

---

## Card 3 — Build auth + users

**Goal**: support real maintainer identities.

**Create / edit**
- `app/api/auth.py` — `/register`, `/login`
- `app/repositories/user_repo.py` — user SQL
- `app/domain/` — request/response models as needed
- `migrations/versions/` — users table migration
- `tests/api/`, `tests/repositories/` — auth coverage

**Done when**
- users can register
- password verification works
- JWT-protected routes reject invalid callers

---

## Card 4 — Build classifier baseline

**Goal**: classify repository issues through a separate inference service.

**Create / edit**
- `model_server/classifier/train.py` — baseline training pipeline
- `model_server/classifier/inference.py` — `/classify`
- `model_server/classifier/model_card.md` — architecture, data hash, metrics
- `app/services/classifier_service.py` — HTTP client wrapper
- `app/api/classifier.py` — public proxy route
- `data/*.jsonl`, `evals/golden_classification.json`, `evals/run_classification_eval.py`

**Done when**
- the model server returns labels
- the main API can proxy a classification request
- baseline metrics are recorded in the model card

---

## Card 5 — Build the RAG pipeline

**Goal**: answer questions from retrieved repository knowledge.

**Create / edit**
- `app/services/rag_service.py` — rewrite → retrieve → rerank → generate
- `app/api/rag.py` — query endpoint
- `app/infra/minio.py` — document storage support
- repositories / migrations for chunks and embeddings
- `prompts/rag_system.txt`
- `evals/golden_rag.json`, `evals/run_rag_eval.py`

**Done when**
- a seeded document can be retrieved
- answers cite supporting chunks
- RAG evals produce measurable scores

---

## Card 6 — Build the memory layer

**Goal**: persist useful long-term facts safely and reviewably.

**Create / edit**
- `app/services/memory_service.py` — TTL cache + vector writes + audits
- `app/repositories/memory_repo.py`, `audit_repo.py`
- `app/api/memory.py`
- `prompts/memory_write.txt`
- migrations for memories and audit events

**Done when**
- approved facts can be written, listed, and deleted
- every write leaves an audit record
- Redis and pgvector responsibilities remain separate

---

## Card 7 — Build chat orchestration

**Goal**: let one conversation coordinate classifier, RAG, and memory tools.

**Create / edit**
- `app/services/chat_service.py`
- `app/api/chat.py`
- `app/domain/chat.py`
- `app/infra/llm.py`, `tracing.py`, `redaction.py`

**Done when**
- `/chat` streams tokens
- tool calls are visible in traces
- sensitive data is redacted before logging

---

## Card 8 — Build the maintainer UI

**Goal**: expose core workflows to a human maintainer.

**Create / edit**
- `chatbot/app.py`
- `chatbot/pages/login.py`
- `chatbot/pages/chat.py`
- `chatbot/pages/memory_inspector.py`
- `chatbot/pages/widget_config.py`

**Done when**
- a maintainer can log in, chat, inspect memory, and create widget config from the browser

---

## Card 9 — Build the embeddable widget

**Goal**: let another site host the copilot with one script tag.

**Create / edit**
- `widget/src/App.jsx`
- `widget/src/useWidgetConfig.js`
- `widget/src/postMessage.js`
- `widget/vite.config.js`
- `app/api/widget.py`
- `demo/host/index.html`, `demo/host/nginx.conf`

**Done when**
- one copied embed snippet loads the widget
- config is fetched at runtime
- iframe resizing works in the demo host

---

## Card 10 — Add evals, tracing, and security checks

**Goal**: make system quality visible before packaging it.

**Create / edit**
- `evals/**`
- `docs/EVALS.md`, `docs/SECURITY.md`, `docs/DECISIONS.md`
- `app/infra/tracing.py`, `redaction.py`
- CI config later, once the commands settle

**Done when**
- CI fails below committed thresholds
- traces show the request tree
- redaction tests cover known leak paths

---

## Card 11 — Dockerize the full stack

**Goal**: build and run the complete system from a clean machine.

**Create / edit**
- `Dockerfile` files for API, model server, chatbot, demo host
- `pyproject.toml` beside each Python-service Dockerfile so each image can build with `uv` from its own service context
- `docker-compose.yml` — add app services and dependencies
- `.dockerignore`
- `docs/RUNBOOK.md` — exact boot and smoke-test commands

**Done when**
- `docker compose up --build` starts the stack
- Python images install dependencies with `uv`
- smoke tests pass against containerized services
- the runbook can be followed without tribal knowledge
