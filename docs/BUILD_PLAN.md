# Build Plan

This is the dependency order for the project. It follows the Week 7 brief, but is written as milestones rather than weekdays so we can work step by step without losing the architecture.

## Milestone board

| Step | Status | Outcome |
| --- | --- | --- |
| 0. Shape the repository | done | the system has clear homes and rules |
| 1. Build the foundation | in progress | the stack boots, secrets resolve, schema exists, dataset exists |
| 2. Build the NLP comparison track | backlog | three classifiers plus NER/summarization are measurable |
| 3. Build advanced RAG | verification pending | retrieval beats the naive baseline with numbers |
| 4. Build the chatbot, memory, and widget surfaces | in progress | a real maintainer workflow exists end to end |
| 5. Harden, package, and ship | backlog | a fresh clone can boot, CI is green, and the demo is ready |

---

## Step 0 — Shape the repository ✅

**Goal**: make the architecture visible before implementation begins.

**Already established**
- root orchestration: `README.md`, `.gitignore`, `.env.example`, `docker-compose.yml`
- Python services with local manifests: `backend/`, `model_server/`, `chatbot/`
- migration runner with its own local manifest: `migrate/`
- frontend surfaces: `widget/`, `demo/host/`
- supporting areas: `prompts/`, `evals/`, `data/`, `migrations/`, `docs/`
- backend boundaries: Pydantic API schemas, thin routers, services, repositories, domain, infra
- fixed Week 7 dataset source: closed issues from `pandas-dev/pandas`

**Done when**
- every future subsystem has a home
- the code boundaries are written down
- the project history and decision log exist

---

## Step 1 — Build the foundation

**Goal**: make the architecture real enough that all later work can stand on it.

### 1.1 Compose the full stack

**Add / complete**
- `docker-compose.yml`
- Python-service Dockerfiles beside their local `pyproject.toml`
- static containers for `widget` and `host`

**Required services**
- `api`
- `chatbot`
- `widget`
- `model-server`
- `host`
- `migrate`
- `db`
- `redis`
- `minio`
- `vault`

**Done when**
- the compose file declares the whole production-shaped stack, not just infra
- `migrate` runs before `api`
- the service names match the architecture and runbook

### 1.2 Wire secrets and startup checks

**Add / complete**
- `backend/app/infra/vault.py`
- `backend/app/main.py`
- `backend/app/core/config.py`
- `docs/SECURITY.md`
- `docs/RUNBOOK.md`

**Done when**
- every real secret is expected from Vault
- `.env` is only for the Vault root token and ports
- the API refuses to boot if Vault is unreachable

### 1.3 Wire tracing from the beginning

**Add / complete**
- `backend/app/infra/tracing.py`
- trace settings in Vault-backed config
- first request-level trace / request ID plumbing
- tracing choice recorded in `docs/DECISIONS.md`

**Done when**
- later LLM, tool, and retrieval spans have a place to attach
- logs and traces can share a trace ID from the start

### 1.4 Establish the database baseline

**Add / complete**
- Alembic config ✅
- `migrations/versions/` first revision ✅
- initial tables: `users`, `widgets`, `audit_log`, `memory`

**Done when**
- schema exists through migrations, not manual SQL
- the `migrate` container can run `alembic upgrade head`
- future schema work has a clean lineage

### 1.5 Build the dataset pipeline

**Add / complete**
- fetch script for closed `pandas-dev/pandas` issues
- label mapping in `docs/DECISIONS.md`
- `data/raw_issues.jsonl`
- normalized `train.jsonl`, `val.jsonl`, `test.jsonl`
- split/count report

**Rules**
- labels map to `bug / feature / docs / question`
- splits are stratified
- test examples are strictly newer in time than training examples

**Done when**
- the raw dataset is fetched
- the mapping is documented
- train/val/test exist and class counts are known

**Current evidence**
- corrected train/validation/test files are present in `data/`
- `split_report.json` records `14,302` normalized examples from `pandas-dev/pandas`
- local `raw_issues.jsonl` is still a zero-byte placeholder because the raw snapshot was intentionally not brought back to the low-space checkout

### 1.6 Start the first fine-tuning run

**Add / complete**
- `model_server/classifier/train_distilbert.py`
- run logging
- first encoder fine-tuning experiment

**Colab usage**
- when we reach this step, the user will run the training notebook in **online Google Colab**
- we will prepare the repo-backed training code / notebook cells at that time, not before
- keep the real training script, config, schema, and outputs defined in this repository
- Colab is the execution surface, not the source of truth

**Done when**
- the first training run has started
- the exact dataset version and run configuration are recoverable

**Current evidence**
- first corrected run: `first-distilbert-freeze4`
- DistilBERT test metrics added: macro-F1 `0.9000`, accuracy `0.9534`
- validation macro-F1: `0.7422`
- validation accuracy: `0.8135`
- run manifest and metrics are committed under `model_server/classifier/runs/`

---

## Step 2 — Build the NLP comparison track

**Goal**: produce the three-model comparison the brief requires, then expose the NLP tools over HTTP.

### 2.1 Finish the fine-tuned classifier

**Add / complete**
- saved model artifact
- artifact upload / manifest in MinIO
- `model_server/classifier/model_card.md`

**Model card must include**
- architecture
- hyperparameters
- training data hash
- freeze policy
- final metrics

### 2.2 Build the two baselines on the same splits

**Add / complete**
- classical ML baseline: TF-IDF + logistic regression ✅ code + Colab metrics added
- LLM baseline on the same 200-row balanced comparison subset ✅ metrics added
- shared evaluation outputs

**Current evidence**
- classical baseline entrypoint: `python -m model_server.classifier.train_tfidf_logreg`
- expected run folder: `model_server/classifier/runs/classical-tfidf-logreg/`
- classical validation macro-F1: `0.7414`
- classical test macro-F1: `0.8847`
- 200-row comparison subset: `data/test_200_balanced.jsonl`
- subset builder: `python -m scripts.dataset.build_comparison_subset`
- OpenAI LLM baseline entrypoint: `python -m model_server.classifier.evaluate_openai_llm`
- OpenAI LLM notebook: `notebooks/llm_openai_baseline_colab.ipynb`
- 200-row macro-F1: DistilBERT `0.8647`, TF-IDF `0.8465`, OpenAI `0.8671`

**Done when**
- all three models are evaluated on `data/test_200_balanced.jsonl` ✅
- accuracy, macro-F1, per-class F1, latency, and OpenAI cost are available ✅

### 2.3 Defend the deployment choice

**Add / complete**
- three-way comparison table in `docs/DECISIONS.md` ✅
- one chosen production model with a numeric defense ✅

**Decision**
- chosen classifier: DistilBERT run `first-distilbert-freeze4`
- reason: OpenAI is only `0.0024` macro-F1 ahead on the 200-row slice, while DistilBERT avoids per-call API cost, rate limits, external dependency, and production secret handling
- TF-IDF remains the fast fallback/baseline, not the primary model

### 2.4 Expose NLP tools through the model server

**Add / complete**
- `/classify` ✅ DistilBERT-backed endpoint added to the model server and Docker-smoke-tested
- backend `/classifier` proxy ✅ calls model server `/classify`
- `/ner` ✅ rule-based code-shaped entity extractor added
- `/summarize` ✅ OpenAI structured-output summarizer added; requires injected API key

**Done when**
- all three are FastAPI endpoints ✅
- the chatbot will later be able to call them over HTTP ✅

**Serving note**
- `CLASSIFIER_MODEL_DIR` points at the saved Hugging Face model directory; model weights remain outside Git.
- Docker smoke result: `POST /classify` returned `bug` with confidence `0.9650` and model artifact SHA-256 `45790f41e45d707aada1b76e87e4b6919e51ea357c40bc1f30a444fe34a6f67a`.
- Docker smoke result: `POST /ner` returned grouped code-shaped entities for function, package/version, Python version, exception, file path, operating system, and file type.
- Docker smoke result: `POST /summarize` returned the expected missing-key `503` until an API key is injected at container startup, then returned a structured `gpt-4o-mini` summary after the key was injected.

### 2.5 Build the classification golden set

**Add / complete**
- `evals/golden_classification.json` ✅
- 25 hand-curated examples ✅
- classifier eval script ✅
- metrics outputs ✅ Docker classifier golden eval: accuracy `0.9600`, macro-F1 `0.9580`

**Done when**
- golden classification examples are separate from the train/test split and from `test_200_balanced.jsonl` ✅
- the same golden set can evaluate all three models ✅

---

## Step 3 — Build advanced RAG

**Goal**: build retrieval that beats the naive baseline and prove each improvement with a number.

### 3.1 Build the corpus

**Corpus must contain**
- project docs ✅ dev corpus scaffold added
- a held-out slice of resolved issues with maintainer answers ⏳ dev corpus starts with held-out issue text; full corpus needs maintainer comments/answers

**Rule**
- held-out RAG issues do not appear in classifier training

**Current dev-corpus rule**
- raw corpus/chunk/index files stay outside Git under ignored `data/rag/` folders
- `data/rag/corpus_manifest.json` is tracked as small reproducibility evidence
- `data/rag/dev_issue_sources.json` tracks only public issue IDs so Colab can rebuild the same dev corpus without committing raw issue text

### 3.2 Choose the embedding model with evidence

This is for RAG/retrieval, not for the issue classifier. The classifier decision above does not force an embedding model.

**Add / complete**
- at least two embedding candidates ✅ `all-MiniLM-L6-v2` and `e5-small-v2` compared
- retrieval-quality comparison on the RAG golden set ✅ best `intfloat/e5-small-v2`, recall@10 `1.0000`, MRR@10 `1.0000`
- chosen model documented in `docs/DECISIONS.md` ✅ D-023

### 3.3 Improve retrieval beyond the naive baseline

**Add / complete**
- naive fixed-size dense baseline ✅ recall@10 `0.8400`, MRR@10 `0.6083`
- non-naive parent-child chunking ✅ recall@10 `0.9200`, MRR@10 `0.7633`
- sparse retrieval such as BM25 ✅ BM25 overall recall@10 `1.0000`, MRR@10 `0.9733`
- dense retrieval in pgvector ⏳ schema, ingest scripts, model-server embedding endpoint, and backend `/rag/query` hybrid retrieval path added; run indexing and smoke tests next
- tuned hybrid weighting ✅ best true hybrid dense `0.25` / sparse `0.75`, recall@10 `1.0000`, MRR@10 `0.9533`
- cross-encoder reranking ✅ `cross-encoder/ms-marco-MiniLM-L-6-v2` over top-25 hybrid candidates, recall@10 `1.0000`, MRR@10 `0.9533`, nDCG@10 `0.9471`
- one query transformation technique ✅ deterministic issue-query expansion preserves recall@10 `1.0000`, MRR@10 `0.9400`; optional/gated because untransformed hybrid ranks slightly better
- metadata filtering ✅ reliable filters preserve best-hybrid recall@10 `1.0000`, MRR@10 `0.9533`
- RAG answer generation over retrieved chunks ✅ model-server `/rag-answer` with retrieval-only fallback

**Done when**
- every move beyond fixed-size dense retrieval is justified by a metric

### 3.4 Build the RAG golden set

**Add / complete**
- `evals/golden_rag.json` ✅
- 25 question / ideal-answer / ground-truth-source triples ✅
- retrieval metrics ✅ naive dense baseline recorded
- five hand-labeled examples for judge-agreement reporting

### 3.5 Add safe logging and exception hardening

**Add / complete**
- `backend/app/infra/redaction.py`
- explicit redaction tests
- domain exception handling mapped at the API boundary

**Done when**
- a fake API key never appears unredacted in logs, traces, or memory
- users receive structured errors, not stack traces

---

## Step 4 — Build the chatbot, memory, and widget surfaces

**Goal**: turn the models and retrieval stack into a maintainer-facing product.

### 4.1 Add authentication and roles

**Add / complete**
- auth endpoints ✅ `/auth/register`, `/auth/login`, `/auth/me`
- JWT signing key from Vault/env ✅ `JWT_SIGNING_KEY`
- `user` and `admin` roles ✅ user records carry role; admin dependency exists for protected admin routes
- memory ownership ✅ memory endpoints use the bearer-token user instead of caller-supplied `user_id`
- admin invite flow

### 4.2 Build the single tool-calling chatbot

**Tools**
- classify ✅ available to the OpenAI tool-calling chat agent
- NER ✅ available to the OpenAI tool-calling chat agent
- summarize ✅ available only when the UI/API explicitly allows the LLM summarizer
- RAG search ✅ available as `rag_search`; returns retrieved chunks/citations to the agent
- explicit `write_memory` ✅ guarded by `allow_memory_write` and backed by pgvector memory records/audit log

**Rule**
- one tool-calling LLM ✅ bounded OpenAI Responses API loop with max 3 tool rounds
- no automatic long-term memory writes

### 4.3 Add memory

**Short-term**
- Redis conversation state ✅ `/chat` saves recent turns by `conversation_id`
- explicit TTL with justification ✅ 2 hours: enough for a work session, short enough to avoid accidental retention

**Long-term**
- pgvector-backed memory ✅ explicit memory writes embed content as passages
- choose one of episodic / semantic / procedural ✅ API supports all three; chat defaults to semantic
- every write creates an audit-log row ✅ repository writes `memory.write`

### 4.4 Build the maintainer UI

**Streamlit pages**
- login ✅ register/login page stores bearer token in Streamlit session state
- chat ✅ initial Streamlit chat page calls backend `/chat`
- memory inspector ✅ lists authenticated user's long-term memories
- widget config admin

### 4.5 Build the embeddable widget

**Add / complete**
- Vite React widget bundle
- collapsed bubble → expanded chat panel
- streamed messages
- runtime theme from widget config
- `/widget.js` loader
- host page under `demo/host/`
- iframe `postMessage` resize channel

### 4.6 Enforce embed security

**Add / complete**
- widget table fields: `widget_id`, `allowed_origins`, `theme`, `greeting`, `enabled_tools`
- CORS allowlist from database config
- `Content-Security-Policy` with `frame-ancestors`

### 4.7 Put both eval suites in CI

**Done when**
- classification and RAG evals both run on push
- thresholds come from `evals/eval_thresholds.yaml`
- regressions fail the build

---

## Step 5 — Harden, package, and ship

**Goal**: make the system explainable, reproducible, and demo-ready.

### 5.1 Prove fresh-clone startup

**Done when**
- `cp .env.example .env`
- `docker compose up`
- the whole stack starts from a clean clone

### 5.2 Run security and correctness checks

**Required**
- `grep -ri 'sk-'`
- `grep -ri 'password'`
- no secrets outside Vault-reading code
- redaction test passes
- lint / type-check / image builds / smoke tests pass

### 5.3 Finish release materials

**Add / complete**
- `README.md`
- `docs/ARCH.md`
- `docs/DECISIONS.md`
- `docs/RUNBOOK.md`
- `docs/EVALS.md`
- `docs/SECURITY.md`
- Git tag `v0.1.0-week7`

### 5.4 Rehearse the Friday proof

**Must be demoable**
- classifier comparison
- trace UI walkthrough, including an error path
- cross-conversation memory recall
- widget on allowed origin
- widget blocked on disallowed origin
- clean CI
