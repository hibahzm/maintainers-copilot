# Project Report

This is the running build journal. Every meaningful change should add a dated entry so future us can reconstruct not only what changed, but why.

## 2026-05-20 — Lightweight CI gate added

### Added
- `.github/workflows/ci.yml`
- `evals/check_eval_results.py`

### Updated
- `docs/BUILD_PLAN.md`
- `docs/REPORT.md`

### Design notes
- CI now runs backend unit tests, Python compile checks, widget build checks, and offline eval evidence checks.
- The eval gate reads `evals/eval_thresholds.yaml` and verifies committed classification macro-F1 plus RAG recall@5 without requiring a model server, OpenAI key, GPU, or pgvector index.
- Live model/RAG evals remain a release/demo verification step because they depend on external services and downloaded artifacts.

## 2026-05-20 — Widget origin enforcement added

### Updated
- `backend/app/api/widget.py`
- `backend/app/core/config.py`
- `backend/app/main.py`
- `backend/app/services/widget_service.py`
- `backend/tests/services/test_widget_service.py`
- `chatbot/pages/widget_config.py`
- `demo/host/nginx.conf`
- `widget/src/App.jsx`
- `widget/src/useWidgetConfig.js`
- `widget/nginx.conf`
- `docs/BUILD_PLAN.md`

### Design notes
- Public widget config now checks the declared host origin against the widget's saved `allowed_origins`.
- The loader passes the host page origin into the iframe, and the React widget sends that origin when fetching config.
- The API now has a centralized CORS allowlist for the local widget, demo host, and Streamlit surfaces.
- The widget and demo host Nginx configs now add local-dev CSP, referrer, and content-type hardening headers, including `frame-ancestors` for the widget.

## 2026-05-20 — Embeddable widget skeleton added

### Updated
- `backend/app/api/widget.py`
- `backend/app/core/config.py`
- `backend/app/services/widget_service.py`
- `docker-compose.yml`
- `widget/src/App.jsx`
- `widget/src/postMessage.js`
- `widget/src/useWidgetConfig.js`
- `widget/src/style.css`
- `demo/host/index.html`
- `docs/BUILD_PLAN.md`

### Design notes
- Backend `/widget/widget.js` now returns a JavaScript loader that injects a fixed bubble and iframe.
- The widget app fetches public widget config, applies runtime theme color, and calls backend `/chat` with non-streaming messages.
- The widget posts resize messages to the host page so the iframe can adjust height.
- The demo host now embeds the loader script. Streaming and origin enforcement are still later hardening steps.

## 2026-05-20 — Widget config admin surface added

### Added
- `backend/tests/services/test_widget_service.py`

### Updated
- `backend/app/api/dependencies.py`
- `backend/app/api/schemas/widget.py`
- `backend/app/api/widget.py`
- `backend/app/repositories/widget_repo.py`
- `backend/app/services/widget_service.py`
- `chatbot/pages/widget_config.py`
- `docs/BUILD_PLAN.md`

### Design notes
- Admin users can upsert and list widget configs through `/widget/admin/...` endpoints.
- Public clients can read safe widget config through `/widget/config/{widget_id}`.
- Widget config stores `widget_id`, `allowed_origins`, `theme`, `greeting`, and `enabled_tools`; enforcement of allowed origins is still a later security step.
- Streamlit now has a real admin widget config form instead of a placeholder.

## 2026-05-20 — Streamlit memory inspector wired to API

### Updated
- `chatbot/pages/memory_inspector.py`
- `docs/BUILD_PLAN.md`

### Design notes
- The Memory Inspector now calls `/memory` with the bearer token stored by the Login page.
- It lists memories owned by the authenticated user and no longer uses a placeholder.

## 2026-05-20 — Streamlit auth page added

### Updated
- `chatbot/pages/login.py`
- `chatbot/pages/chat.py`
- `docs/BUILD_PLAN.md`

### Design notes
- The Streamlit Login page now supports register and login against `/auth/register` and `/auth/login`.
- Successful auth stores the access token and user profile in `st.session_state`.
- The Chat page reuses that token automatically, so explicit memory writes are tied to the authenticated user.

## 2026-05-20 — Auth wired into chat and memory ownership

### Updated
- `backend/app/api/chat.py`
- `backend/app/api/dependencies.py`
- `backend/app/api/memory.py`
- `backend/app/api/schemas/chat.py`
- `backend/app/api/schemas/memory.py`
- `backend/app/services/chat_tools/runner.py`
- `backend/app/services/memory_service.py`
- `chatbot/pages/chat.py`
- `docs/BUILD_PLAN.md`

### Design notes
- `/memory` now requires a bearer token and always reads/writes memories for the authenticated user.
- `/chat` accepts an optional bearer token. If present, explicit memory tool calls use that authenticated user; if absent, memory writes stay blocked.
- Request bodies no longer accept arbitrary `user_id` for chat or memory writes.
- The Streamlit chat page now accepts an access token instead of a manual user ID.

## 2026-05-20 — Auth and roles foundation added

### Added
- `backend/tests/services/test_auth_service.py`

### Updated
- `backend/app/api/auth.py`
- `backend/app/api/dependencies.py`
- `backend/app/api/schemas/auth.py`
- `backend/app/core/config.py`
- `backend/app/repositories/user_repo.py`
- `backend/app/services/auth_service.py`
- `docker-compose.yml`
- `docs/BUILD_PLAN.md`

### Design notes
- `/auth/register` and `/auth/login` now create and validate users against the existing `users` table.
- Passwords are hashed with PBKDF2-SHA256 using per-password salts.
- Access tokens are signed HS256 JWTs using `JWT_SIGNING_KEY`; local compose has a dev-only default and production should inject it from Vault/secrets.
- User records carry `user` or `admin` roles. `CurrentUserDep` and `AdminUserDep` are available for protected endpoints.
- `user` means normal chat/memory ownership. `admin` means product configuration privileges such as widget/tool/admin pages.

## 2026-05-20 — Chat agent prompt moved beside backend agent code

### Added
- `backend/app/services/chat_agent/prompts/agent_system.txt`

### Updated
- `backend/app/services/chat_agent/openai_agent.py`
- `backend/tests/services/test_openai_chat_agent_service.py`

### Design notes
- The OpenAI chat-agent system prompt is now a backend-local prompt file instead of an inline Python string.
- Keeping the prompt beside the agent service makes prompt changes reviewable without mixing policy text into orchestration code.
- Root-level `prompts/` remains for experiment/evaluation prompts such as the classifier LLM baseline.

## 2026-05-20 — OpenAI tool-calling chat agent added

### Added
- `backend/app/services/chat_agent/`
- `backend/tests/services/test_openai_chat_agent_service.py`

### Updated
- `backend/app/api/dependencies.py`
- `backend/app/core/config.py`
- `backend/app/services/chat_service.py`
- `backend/tests/services/test_chat_service.py`
- `docker-compose.yml`
- `docs/BUILD_PLAN.md`
- `docs/DECISIONS.md`

### Design notes
- `/chat` now prefers a bounded OpenAI Responses API function-calling loop when an OpenAI key is configured.
- The agent can call `rag_search`, `classify_issue`, `extract_entities`, `summarize_issue`, and `write_memory`.
- Tool execution remains in backend-owned code. The model chooses tools, but it never directly touches databases, Redis, model-server internals, or memory writes.
- The loop is capped at three tool rounds to avoid infinite tool-call chains.
- If no OpenAI key is configured, the existing deterministic routing path remains as a local no-cost fallback.

## 2026-05-20 — Chat tool code split into dedicated service package

### Added
- `backend/app/services/chat_tools/`

### Removed
- `backend/app/services/maintainer_tools_service.py`

### Updated
- `backend/app/api/dependencies.py`
- `backend/app/services/chat_service.py`
- `backend/pyproject.toml`
- `backend/tests/services/test_chat_service.py`

### Design notes
- `ChatService` is now focused on conversation orchestration: short-term memory, response flow, and RAG fallback.
- Tool-specific responsibilities moved into `chat_tools`: model-server calls, tool selection, execution, text normalization, and answer rendering.
- This keeps the code ready for auth/roles without mixing identity logic into classifier/NER/summarizer/memory tool code.
- Backend package metadata now declares `app` as the Hatch wheel package so `uv run --project backend ...` can build the project cleanly.

## 2026-05-20 — Short-term Redis conversation memory added

### Added
- `backend/app/services/conversation_state_service.py`

### Updated
- `backend/app/api/dependencies.py`
- `backend/app/core/config.py`
- `backend/app/infra/redis_client.py`
- `backend/app/services/chat_service.py`
- `backend/tests/services/test_chat_service.py`
- `docker-compose.yml`
- `docs/BUILD_PLAN.md`

### Design notes
- `/chat` now loads and saves recent conversation turns in Redis by `conversation_id`.
- The Redis TTL is 2 hours, which is long enough for one maintainer work session but short enough to avoid accidental retention.
- Short-term memory is best-effort: if Redis is unavailable, chat still answers instead of failing the whole turn.

## 2026-05-20 — Explicit long-term memory path added

### Added
- `migrations/versions/20260520_0004_memory_vector_index.py`

### Updated
- `backend/app/api/chat.py`
- `backend/app/api/dependencies.py`
- `backend/app/api/memory.py`
- `backend/app/api/schemas/chat.py`
- `backend/app/api/schemas/memory.py`
- `backend/app/repositories/memory_repo.py`
- `backend/app/services/chat_service.py`
- `backend/app/services/memory_service.py`
- `backend/tests/services/test_chat_service.py`
- `chatbot/pages/chat.py`
- `docs/BUILD_PLAN.md`

### Design notes
- Long-term memory writes are explicit only; normal chat turns are not automatically saved.
- Memory content is embedded through the model-server `/embed` endpoint as `passage` text and stored in pgvector.
- Each memory write creates a `memory.write` audit-log row. Until auth is finished, memory calls require an explicit `user_id`.

## 2026-05-20 — Chatbot NLP tool routing added

### Added
- `backend/app/services/maintainer_tools_service.py`

### Updated
- `backend/app/api/chat.py`
- `backend/app/api/dependencies.py`
- `backend/app/api/schemas/chat.py`
- `backend/app/services/chat_service.py`
- `backend/tests/services/test_chat_service.py`
- `chatbot/pages/chat.py`
- `docs/BUILD_PLAN.md`

### Design notes
- `/chat` can now route explicit maintainer-tool requests to classifier, NER, and summarizer tools.
- Classifier and NER are local model-server tools. Summarizer is guarded by `allow_summarizer=false` by default because it may call OpenAI.
- General questions still fall back to the RAG tool, so Step 4 now has a real chatbot surface over Step 2 and Step 3.

## 2026-05-20 — Chatbot RAG orchestration started

### Added
- `backend/tests/services/test_chat_service.py`

### Updated
- `backend/app/api/chat.py`
- `backend/app/api/schemas/chat.py`
- `backend/app/services/chat_service.py`
- `backend/app/api/dependencies.py`
- `chatbot/pages/chat.py`
- `docs/BUILD_PLAN.md`

### Design notes
- Backend `/chat` now returns a real `ChatResponse` instead of a feature stub.
- `ChatService` uses RAG as the first tool and returns citations/tool metadata.
- The Streamlit chat page sends conversation turns to the backend and displays answers, citations, and tool details.
- This is Step 4 scaffolding; classifier/NER/summarizer tool routing and memory-aware behavior remain next.

## 2026-05-20 — RAG answer generation hook added

### Added
- `model_server/routers/rag_answer.py`
- `model_server/schemas/rag_answer.py`
- `model_server/services/rag_answer.py`
- `model_server/tests/test_rag_answer_router.py`

### Updated
- `backend/app/api/rag.py`
- `backend/app/api/schemas/rag.py`
- `backend/app/services/rag_service.py`
- `backend/tests/services/test_rag_service.py`
- `docker-compose.yml`
- `model_server/main.py`
- `data/rag/README.md`
- `docs/BUILD_PLAN.md`

### Design notes
- Model-server now has `/rag-answer`, an OpenAI structured-output endpoint that answers from retrieved chunks and returns citation source IDs.
- Backend `/rag/query` calls `/rag-answer` after retrieval when `generate_answer=true`.
- If the OpenAI key is missing or answer generation fails, `/rag/query` falls back to retrieval-only output instead of hiding the retrieved evidence.

## 2026-05-20 — Runtime RAG hybrid retrieval added

### Added
- `migrations/versions/20260520_0003_rag_sparse_search.py`
- `backend/tests/repositories/test_rag_repo.py`

### Updated
- `backend/app/repositories/rag_repo.py`
- `backend/app/services/rag_service.py`
- `backend/app/api/schemas/rag.py`
- `backend/app/domain/rag.py`
- `backend/tests/services/test_rag_service.py`
- `data/rag/README.md`
- `docs/BUILD_PLAN.md`

### Design notes
- Runtime `/rag/query` now uses hybrid retrieval, not dense-only retrieval.
- Dense candidates come from pgvector cosine search over `rag_chunks.embedding`.
- Sparse candidates come from PostgreSQL full-text search over generated `rag_chunks.search_vector`.
- Results are merged with the measured dense `0.25` / sparse `0.75` weighting and expose both dense and sparse raw scores for debugging.

## 2026-05-20 — Runtime RAG retrieval path added

### Added
- `model_server/routers/embedder.py`
- `model_server/schemas/embedder.py`
- `model_server/services/embedder.py`
- `backend/app/domain/rag.py`
- `backend/app/repositories/rag_repo.py`
- `backend/tests/services/test_rag_service.py`
- `model_server/tests/test_embedder_router.py`

### Updated
- `backend/app/api/rag.py`
- `backend/app/api/schemas/rag.py`
- `backend/app/services/rag_service.py`
- `backend/app/api/dependencies.py`
- `backend/app/core/config.py`
- `model_server/main.py`
- `docker-compose.yml`

### Design notes
- Model-server now exposes `/embed` for E5 query/passsage embeddings without adding `sentence-transformers`; it uses `transformers` + CPU Torch already present in the model-server image.
- Backend `/rag/query` now embeds the user question through model-server, queries `rag_chunks` in pgvector, and returns citations plus retrieved chunks.
- LLM answer generation is intentionally not mixed into this step; retrieval can be tested first, then answer synthesis/reranking can be layered on top.

## 2026-05-20 — RAG ingest uv index strategy fixed

### Updated
- `scripts/rag/ingest_pgvector.sh`

### Design notes
- `uv` requires `--index-strategy unsafe-best-match` when resolving the PyTorch `+cpu` wheel across the PyTorch CPU index and PyPI.
- This is scoped only to the local ingest wrapper, not the service dependency lock.

## 2026-05-20 — RAG ingest pins CPU Torch

### Updated
- `scripts/rag/ingest_pgvector.sh`
- `data/rag/README.md`

### Design notes
- The ingest wrapper now pins `torch==2.5.1+cpu` from the PyTorch CPU wheel index.
- This prevents `uv` from resolving CUDA/NVIDIA packages during local pgvector ingestion.

## 2026-05-20 — RAG pgvector ingest wrapper added

### Added
- `scripts/rag/ingest_pgvector.sh`

### Updated
- `data/rag/README.md`

### Design notes
- The ingest wrapper replaces a long error-prone command with one script.
- It forces CPU PyTorch wheels by default so local indexing does not download large CUDA/NVIDIA packages.
- Heavy embedding dependencies remain runtime-only for ingestion and are not added to backend/model-server dependencies.

## 2026-05-20 — pgvector RAG indexing foundation added

### Added
- `migrations/versions/20260520_0002_rag_tables.py`
- `scripts/rag/ingest_pgvector.py`
- `scripts/rag/query_pgvector.py`

### Updated
- `docs/BUILD_PLAN.md`
- `docs/DECISIONS.md`
- `data/rag/README.md`

### Design notes
- The new migration creates `rag_sources` and `rag_chunks`, with `rag_chunks.embedding` as `vector(384)` for the selected `intfloat/e5-small-v2` embedding model.
- The indexing script embeds parent-child chunks with the E5 `passage:` prefix and stores vectors in pgvector.
- The query smoke script embeds user questions with the E5 `query:` prefix and searches pgvector by cosine distance.
- This wires the required pgvector store without adding `sentence-transformers` to the backend Docker image yet. Runtime API integration remains the next slice.

## 2026-05-20 — RAG embedding model selected

### Added
- `evals/rag_embedding_model_comparison_results.json`

### Updated
- `docs/DECISIONS.md`
- `docs/BUILD_PLAN.md`
- `data/rag/README.md`

### Evidence
- compared models: `sentence-transformers/all-MiniLM-L6-v2`, `intfloat/e5-small-v2`
- evaluation mode: dense-only cosine retrieval, metadata filters disabled
- golden examples: `25`
- selected model: `intfloat/e5-small-v2`
- selected recall@10: `1.0000`
- selected MRR@10: `1.0000`
- selected nDCG@10: `0.9636`

### Design notes
- `e5-small-v2` beats `all-MiniLM-L6-v2` on ranking quality while both reach recall@10 `1.0000`.
- This closes the embedding-choice requirement for the dev RAG stack; pgvector wiring can now use the selected embedding dimension/model.

## 2026-05-20 — Embedding eval metadata filter disabled

### Updated
- `notebooks/rag_embedding_model_comparison_colab.ipynb`
- `data/rag/README.md`
- `scripts/rag/build_dev_corpus.py`
- `data/rag/dev_issue_sources.json`

### Design notes
- Embedding model comparison now runs with `--no-metadata-filter` so the dense model choice is measured directly, not dominated by issue-label metadata availability.
- Tracked dev issue references now include the intended target label, which makes future GitHub fallback rebuilds less sensitive to label changes on the public issue tracker.
- If Colab has already built `data/rag/chunks/parent_child_chunks.jsonl`, the embedding comparison can be rerun directly without cloning or rebuilding the corpus again.

## 2026-05-20 — RAG corpus rebuild guardrails added

### Added
- `data/rag/dev_issue_sources.json`

### Updated
- `scripts/rag/build_dev_corpus.py`
- retrieval evaluation scripts under `scripts/rag/`
- `data/rag/README.md`
- `docs/BUILD_PLAN.md`

### Design notes
- Fresh Colab clones do not include ignored JSONL data files, so `build_dev_corpus` can now rebuild the dev issue corpus from tracked public issue IDs by fetching issue bodies from GitHub.
- Retrieval evaluators now validate that every golden-set source ID exists in the chunk corpus before scoring. This prevents silently valid-looking but misleading metrics when the corpus only contains project docs.
- The first embedding result brought back from Colab was intentionally not committed because it was generated from an incomplete 9-document corpus. It should be regenerated after this guardrail fix.

## 2026-05-20 — RAG embedding comparison evaluator added

### Added
- `scripts/rag/evaluate_embedding_models.py`
- `notebooks/rag_embedding_model_comparison_colab.ipynb`

### Updated
- `data/rag/README.md`
- `docs/BUILD_PLAN.md`
- `.gitignore`

### Design notes
- The evaluator compares dense embedding candidates directly on the RAG golden set using parent-child chunks.
- It is kept as an experiment/Colab dependency so `sentence-transformers` does not bloat the local Docker images before the model choice is justified.
- Default candidates are `sentence-transformers/all-MiniLM-L6-v2` and `intfloat/e5-small-v2`; the output file is `evals/rag_embedding_model_comparison_results.json`.

## 2026-05-20 — Cross-encoder RAG rerank results recorded

### Added
- `evals/rag_cross_encoder_rerank_results.json`
- `notebooks/rag_cross_encoder_rerank_colab.ipynb`

### Updated
- `data/rag/README.md`
- `docs/BUILD_PLAN.md`

### Evidence
- first-stage retriever: parent-child hybrid dense `0.25` / sparse `0.75`
- reranker: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- candidate_k: `25`
- recall@10: `1.0000`
- MRR@10: `0.9533`
- nDCG@10: `0.9471`

### Design notes
- Cross-encoder reranking preserves perfect recall@10 and the best true-hybrid MRR@10 while improving nDCG@10 versus the unreranked true hybrid (`0.9471` vs `0.9355`).
- The reranker remains an experiment/runtime component for now; it is not added to the model-server Docker image.

## 2026-05-20 — Cross-encoder RAG rerank evaluator added

### Added
- `scripts/rag/evaluate_cross_encoder_rerank.py`

### Updated
- `data/rag/README.md`
- `docs/BUILD_PLAN.md`
- `.gitignore`

### Design notes
- Cross-encoder reranking is kept in the experiment path, not the Docker model-server dependency set, because it downloads a separate transformer reranker.
- The evaluator reranks the top 25 candidates from the tuned hybrid retriever and writes `evals/rag_cross_encoder_rerank_results.json`.
- This step is ready for Colab execution; the metric evidence becomes complete once the small JSON result file is brought back into the repo.

## 2026-05-20 — RAG query transformation evaluated

### Added
- `scripts/rag/evaluate_query_transform.py`
- `evals/rag_query_transform_results.json`
- `evals/rag_query_transform_unfiltered_results.json`

### Evidence
- base retriever: parent-child hybrid dense `0.25` / sparse `0.75`
- query technique: deterministic issue-query expansion
- changed golden queries: `17` / `25`
- recall@10: `1.0000`
- MRR@10: `0.9400`
- nDCG@10: `0.9292`

### Design notes
- The query transform preserves perfect recall@10 on the current dev corpus.
- It slightly hurts ranking quality versus the untransformed best true hybrid, which has MRR@10 `0.9533` and nDCG@10 `0.9355`.
- We keep this as an implemented, measured technique, but it should be gated for underspecified queries rather than always enabled.

## 2026-05-20 — RAG metadata filtering evaluated

### Added
- `evals/rag_hybrid_metadata_filter_results.json`

### Updated
- `evals/golden_rag.json`

### Evidence
- retrieval stack: parent-child chunks + BM25/hash-dense hybrid
- metadata fields used: `source_type` and issue `label`
- best true hybrid with filters: dense `0.25` / sparse `0.75`
- filtered recall@10: `1.0000`
- filtered MRR@10: `0.9533`
- filtered nDCG@10: `0.9355`

### Design notes
- Metadata filtering is implemented and measured as an optional retrieval constraint.
- Two issue golden-set filters were corrected to match the actual corpus label metadata rather than inferring labels from issue title prefixes.
- On the current dev corpus, reliable metadata filters preserve the best unfiltered hybrid score. This means filtering is safe when metadata is reliable, but it should not be forced when the query does not carry trustworthy metadata.

## 2026-05-20 — BM25 and hybrid RAG tuning evaluated

### Added
- `scripts/rag/evaluate_hybrid_retrieval.py`
- `evals/rag_hybrid_tuning_results.json`

### Evidence
- chunking strategy: parent-child sections
- sparse method: BM25
- dense method: hash-dense cosine
- tuned weights: dense `{0.0, 0.25, 0.5, 0.65, 0.75, 0.85, 1.0}`
- best overall: dense `0.0` / sparse `1.0`
- best overall recall@10: `1.0000`
- best overall MRR@10: `0.9733`
- best true hybrid: dense `0.25` / sparse `0.75`
- best true hybrid recall@10: `1.0000`
- best true hybrid MRR@10: `0.9533`

### Design notes
- The tiny dev corpus is lexical enough that pure BM25 wins overall, which is useful evidence rather than a failure.
- The best true hybrid still beats the parent-child dense-only run on every tracked metric, satisfying the sparse+dense hybrid requirement with a tuned weighting.
- The chosen hybrid setting for the next RAG stage is dense `0.25` / sparse `0.75` unless later full-corpus evidence changes it.

## 2026-05-20 — RAG golden set and naive dense baseline added

### Added
- `evals/golden_rag.json`
- `scripts/rag/chunk_corpus.py`
- `scripts/rag/evaluate_retrieval.py`
- `data/rag/chunks/naive_fixed_chunks_manifest.json`
- `evals/rag_naive_dense_baseline_results.json`

### Evidence
- golden examples: `25`
- naive chunks: `185`
- baseline: fixed-size word chunks + hash-dense cosine retrieval
- recall@1: `0.4800`
- recall@3: `0.7600`
- recall@5: `0.8000`
- recall@10: `0.8400`
- MRR@10: `0.6083`
- nDCG@10: `0.6412`

### Design notes
- This is the intentionally weak baseline required by the rubric: naive fixed-size chunking plus pure dense retrieval.
- The baseline uses a deterministic local hash-dense embedding so the first eval has no API cost and no new heavyweight dependency.
- Later advanced RAG work must beat this baseline with numbers before we claim improvements.

## 2026-05-20 — Parent-child RAG chunking evaluated

### Added
- `scripts/rag/chunk_parent_child.py`
- `data/rag/chunks/parent_child_chunks_manifest.json`
- `evals/rag_parent_child_dense_results.json`

### Evidence
- parent sections: `495`
- child chunks: `609`
- retrieval method held constant: hash-dense cosine retrieval
- recall@1: `0.6800` vs baseline `0.4800`
- recall@3: `0.8000` vs baseline `0.7600`
- recall@5: `0.9200` vs baseline `0.8000`
- recall@10: `0.9200` vs baseline `0.8400`
- MRR@10: `0.7633` vs baseline `0.6083`
- nDCG@10: `0.7881` vs baseline `0.6412`

### Design notes
- Parent-child chunking beats the naive fixed-size dense baseline on every tracked retrieval metric.
- The evaluator now counts each relevant source only once for nDCG so duplicate chunks from the same source do not inflate ranking quality.

## 2026-05-20 — RAG dev corpus workspace added

### Added
- `data/rag/README.md`
- `data/rag/corpus_manifest.json`
- ignored local RAG folders: `data/rag/raw/`, `data/rag/chunks/`, `data/rag/indexes/`
- `scripts/rag/build_dev_corpus.py`

### Updated
- `.gitignore`
- `docs/BUILD_PLAN.md`

### Design notes
- Step 3 starts with a small local dev corpus so we can build and evaluate RAG logic without downloading the full pandas docs/issues corpus locally.
- Raw corpus rows, chunks, and indexes stay out of Git; only small manifests and metrics are tracked.
- The initial dev corpus builder uses project Markdown docs plus held-out issue text from the ignored `data/test_200_balanced.jsonl` file when available.
- The full rubric corpus still needs resolved issues with maintainer answers/comments; that belongs in the later MinIO-backed corpus.

## 2026-05-20 — Golden classification eval completed

### Added
- `evals/classification_eval_results.json`

### Evidence
- endpoint: `http://localhost:8001/classify`
- examples: `25`
- accuracy: `0.9600`
- macro-F1: `0.9580`
- label supports: bug `7`, feature `6`, docs `6`, question `6`

### Error analysis
- One miss: `golden-classification-023` expected `question`, predicted `feature` with confidence `0.4877`.
- Bug and docs classes were perfect on this golden set; the remaining ambiguity is between question/help-seeking and feature/request language.

## 2026-05-20 — NLP tool smoke tests recorded

### Verified
- `POST /classify`
- `POST /ner`
- `POST /summarize` missing-key failure path
- `POST /summarize` OpenAI success path

### Evidence
- Classifier predicted `bug` with confidence `0.9649578332901001`.
- Classifier response included model artifact SHA-256 `45790f41e45d707aada1b76e87e4b6919e51ea357c40bc1f30a444fe34a6f67a`.
- NER extracted `read_csv`, `pandas 2.2`, `Python 3.12`, `ValueError`, `pandas/io/parsers.py`, `windows`, and `csv`.
- Summarizer returned the expected missing-key error when no key was injected at container startup.
- Summarizer returned structured JSON with `summary`, `key_points`, `affected_entities`, `maintainer_next_steps`, `risk_level`, `model_name`, `provider`, and `response_id` after an OpenAI key was injected at container startup.

### Follow-up
- Improved NER so snake_case symbols such as `read_csv` are extracted as functions even when written without parentheses.
- Removed `python` from generic package matching so `Python 3.12` is treated as a Python runtime version rather than a package version.

## 2026-05-20 — Model-server pip install tolerates slow networks

### Updated
- `model_server/Dockerfile`

### Design notes
- Added longer pip timeout/retry settings for the `uv` install step after Docker timed out downloading the `uv` wheel from PyPI.
- Disabled the pip progress bar to reduce noisy build output during slow WSL/Docker downloads.
- This does not change runtime behavior; it only makes dependency installation more resilient.

## 2026-05-20 — Model-server Docker dependency install hardened

### Updated
- `model_server/Dockerfile`
- `model_server/pyproject.toml`
- `model_server/services/ner.py`

### Design notes
- Removed `spacy` from runtime dependencies because the implemented NER tool is deterministic regex/rules and does not need spaCy.
- This avoids pulling spaCy's dependency chain during Docker builds, including the `wasabi` wheel that timed out in WSL.
- Added Docker BuildKit cache mounts for pip and uv so repeated dependency installs can reuse downloaded wheels after rebuilds/retries.
- Increased `UV_HTTP_TIMEOUT` to make slow package downloads less brittle.

## 2026-05-19 — Model-server Docker build avoids GHCR uv image

### Updated
- `model_server/Dockerfile`

### Design notes
- Replaced the `COPY --from=ghcr.io/astral-sh/uv:0.11.11` build stage with `pip install uv==0.11.11`.
- This avoids Docker credential-helper failures when WSL/Docker cannot read GHCR metadata.
- The runtime dependency install still uses `uv sync`; only the way `uv` enters the image changed.

## 2026-05-19 — NER and LLM summarizer tools added

### Added
- rule-based `/ner` endpoint for code-shaped entities
- OpenAI-backed `/summarize` endpoint with structured output
- NER and summarizer service/router tests

### Updated
- `model_server/pyproject.toml`
- `.env.example`
- `docker-compose.yml`
- `docs/BUILD_PLAN.md`
- `docs/RUNBOOK.md`
- `docs/SECURITY.md`

### Design notes
- NER is integration-only and deterministic: it extracts functions, dotted symbols, exceptions, package/version mentions, file paths, URLs, operating systems, and file types without an LLM call.
- Summarization uses OpenAI structured output with default model `gpt-4o-mini`, matching the project definition that summarization may be pre-trained or LLM-driven.
- The summarizer returns `503` when no API key is injected, so Docker can still boot without a secret and the key can remain in Vault/secrets.

## 2026-05-19 — Classifier Docker smoke test passed

### Verified
- `docker compose up --build model-server`
- `POST /classify`

### Evidence
- input title: `BUG: read_csv crashes on empty file`
- predicted label: `bug`
- confidence: `0.9649578332901001`
- model artifact SHA-256: `45790f41e45d707aada1b76e87e4b6919e51ea357c40bc1f30a444fe34a6f67a`

### Design notes
- The model-server container successfully loaded the mounted DistilBERT artifact from `/app/artifacts/classifier/first-distilbert-freeze4/model`.
- This completes the real runtime smoke test for the selected classifier endpoint.

## 2026-05-19 — Classifier model artifact fingerprint added

### Added
- `model_server/services/artifacts.py`
- `scripts/artifacts/fingerprint_model.py`
- `model_server/tests/test_artifacts.py`

### Updated
- `model_server/schemas/classifier.py`
- `model_server/services/classifier.py`
- `backend/app/api/schemas/classifier.py`
- `docs/RUNBOOK.md`

### Design notes
- The model-server classifier response now includes `model_artifact_sha256` so eval results can identify the exact local model artifact used.
- The artifact fingerprint is computed from file paths, file sizes, and per-file SHA-256 values; the model weights remain outside Git.
- Added a small script to print the same fingerprint for Drive/MinIO/local artifact manifests without starting the server.

## 2026-05-19 — Dataset rows removed from Git and Docker context

### Updated
- `.gitignore`
- `.dockerignore`
- `data/README.md`

### Design notes
- Added `data/*.jsonl` to `.gitignore` because public issue bodies can still contain user-pasted secrets or secret-like examples.
- Removed tracked JSONL dataset rows from Git while keeping them available locally/externally in Drive or future MinIO.
- Added dataset, notebook, PDF, classifier training/eval, and classifier run artifacts to `.dockerignore` so Docker builds contain only runtime code and not experiment data.
- Kept dataset reports and model metrics tracked as small reproducibility evidence.

## 2026-05-19 — Model-server runtime split by layer

### Added
- `model_server/routers/`
- `model_server/schemas/`
- `model_server/services/`

### Updated
- `model_server/main.py`
- `model_server/tests/test_classifier_router.py`

### Removed
- `model_server/classifier/inference.py`
- placeholder `model_server/ner/inference.py`
- placeholder `model_server/summarizer/inference.py`

### Design notes
- Routers now own only HTTP concerns.
- Schemas now own only Pydantic request/response contracts.
- Services now own model/business logic.
- The classifier service still imports classifier-specific text/training constants from `model_server/classifier/`, which remains the home for classifier training/eval helpers and the model card.
- NER and summarization now have the same router/schema/service shape even while their services are still placeholders.

## 2026-05-19 — NER runtime dependency stabilized

### Updated
- `model_server/pyproject.toml`

### Design notes
- Added `spacy` back to the model-server runtime dependencies because the project brief includes NER as part of the NLP pipeline work.
- This prepares the `/ner` endpoint without adding a separate downloaded spaCy model artifact yet.
- The intended first NER implementation can use lightweight spaCy tokenization/rules for maintainer entities such as package names, versions, file paths, functions, errors, and operating systems.
- Torch remains pinned to the PyTorch CPU wheel index for classifier inference.

## 2026-05-19 — Local classifier artifact mounted for model server

### Updated
- `docker-compose.yml`
- `.dockerignore`
- `docs/RUNBOOK.md`

### Design notes
- Mounted host `./artifacts` into the `model-server` container as read-only `/app/artifacts`, so local model weights can be used without committing them.
- Set the container's `CLASSIFIER_MODEL_DIR` to the mounted DistilBERT model path.
- Added `artifacts/` to `.dockerignore` so Docker builds do not send local model weights in the build context.

## 2026-05-19 — Model-server dependencies trimmed

### Updated
- `model_server/pyproject.toml`

### Design notes
- Removed `spacy` from runtime dependencies because `/ner` is still a stub and no model-server code imports spaCy yet.
- Kept `transformers` and `torch` in runtime because `/classify` loads the selected DistilBERT model.
- Pinned `torch` to the PyTorch CPU wheel index for the model server, so Docker/runtime does not pull GPU/CUDA packages.
- Removed the optional `train` dependency group from the model server because training/comparison now lives in Colab notebooks, not the deployed app runtime.

## 2026-05-19 — Classification golden set added

### Added
- `evals/golden_classification.json`
- `evals/run_classification_eval.py`

### Evidence shape
- 25 synthetic, hand-curated issue examples
- label mix: 7 `bug`, 6 `feature`, 6 `docs`, 6 `question`
- no overlap with `data/test_200_balanced.jsonl`

### Design notes
- The golden set is intentionally separate from train/test data so it can act as a compact human-reviewed regression suite.
- The eval runner calls any classifier-compatible endpoint and computes accuracy, macro-F1, and per-label precision/recall/F1.

## 2026-05-19 — DistilBERT classifier serving endpoint added

### Added
- real model-server `POST /classify` endpoint backed by the selected DistilBERT artifact path
- backend `POST /classifier` proxy service
- classifier serving tests with fake model/server clients

### Updated
- `CLASSIFIER_MODEL_DIR` documented as the runtime model path
- Step 2.4 progress recorded in `docs/BUILD_PLAN.md`

### Design notes
- Model weights are still not committed. The serving code expects the saved Hugging Face model directory to be mounted or copied into the runtime path.
- The model server returns `label`, `confidence`, per-label `scores`, `model_name`, and `model_dir`.

## 2026-05-19 — DistilBERT selected as classifier deployment model

### Updated
- `docs/DECISIONS.md`
- `docs/BUILD_PLAN.md`
- `model_server/classifier/model_card.md`

### Decision
- Selected `first-distilbert-freeze4` as the project issue classifier.
- Kept TF-IDF as the fast fallback/baseline.
- Kept OpenAI `gpt-4o-mini` as the measured LLM reference, not the runtime classifier.

### Rationale
- DistilBERT is effectively tied with OpenAI on the 200-row balanced comparison (`0.8647` vs `0.8671` macro-F1).
- DistilBERT avoids per-call API cost, rate limits, external availability, and production OpenAI secret handling for classification.
- Embedding-model selection remains a separate RAG decision in Step 3.

## 2026-05-19 — 200-row classifier comparison results added

### Added
- `model_server/classifier/runs/first-distilbert-freeze4-test-200/test_metrics.json`
- `model_server/classifier/runs/first-distilbert-freeze4-test-200/classification_report.json`
- `model_server/classifier/runs/classical-tfidf-logreg-test-200/run_manifest.json`
- `model_server/classifier/runs/classical-tfidf-logreg-test-200/metrics.json`
- `model_server/classifier/runs/classical-tfidf-logreg-test-200/classification_report.json`
- `model_server/classifier/runs/openai-gpt-4o-mini-test-200/run_manifest.json`
- `model_server/classifier/runs/openai-gpt-4o-mini-test-200/metrics.json`
- `model_server/classifier/runs/openai-gpt-4o-mini-test-200/classification_report.json`

### Evidence
- DistilBERT 200-row macro-F1: `0.8647`
- TF-IDF Logistic Regression 200-row macro-F1: `0.8465`
- OpenAI `gpt-4o-mini` 200-row macro-F1: `0.8671`
- OpenAI estimated cost for the 200-row run: `$0.0179`

### Design notes
- Step 2.2 now has fair three-way classifier evidence on the same sampled test examples.
- OpenAI is narrowly best on macro-F1, but the difference from DistilBERT is very small; the deployment decision should consider latency, cost, operational simplicity, and whether the model server should depend on an external API.

## 2026-05-19 — Balanced 200-row classifier comparison path added

### Added
- `scripts/dataset/build_comparison_subset.py`
- `data/test_200_balanced.jsonl`
- `data/test_200_balanced_report.json`
- 200-row run landing zones under `model_server/classifier/runs/`

### Updated
- OpenAI baseline now defaults to `data/test_200_balanced.jsonl` with batched requests (`BATCH_SIZE = 20`)
- DistilBERT and classical Colab notebooks now write separate 200-row comparison evidence instead of overwriting full-test evidence
- docs now separate full temporal-test evidence, 200-row three-way comparison, and the later 25-example golden set

### Design notes
- The full `data/test.jsonl` remains unchanged and remains useful for cheap local model evidence.
- The 200-row subset gives a fair, affordable comparison surface for DistilBERT, TF-IDF, and OpenAI on exactly the same examples.
- The future 25-example golden classification set remains a separate hand-reviewed eval, not a replacement for this sampled comparison subset.


## 2026-05-19 — OpenAI LLM baseline scaffold added

### Added
- `model_server/classifier/evaluate_openai_llm.py`
- `notebooks/llm_openai_baseline_colab.ipynb`
- `model_server/classifier/runs/openai-gpt-4o-mini-test-200/README.md`

### Updated
- `model_server/pyproject.toml`
- `docs/COLAB_TRAINING.md`
- `docs/DECISIONS.md`
- `docs/BUILD_PLAN.md`
- `docs/SECURITY.md`
- `model_server/classifier/model_card.md`

### Design notes
- The third classifier track is now isolated like the other two: a repo command, a standalone Colab notebook, and a dedicated run folder.
- The OpenAI baseline uses Responses API Structured Outputs so labels are schema-constrained to `bug / feature / docs / question`; the evaluator parses the JSON and rejects unsupported labels before scoring.
- The notebook defaults to a 50-example pilot to prevent accidental spend; the final evidence uses `FINAL_RUN = True` on the 200-row balanced comparison subset.

## 2026-05-19 — DistilBERT temporal test results added

### Added
- `model_server/classifier/runs/first-distilbert-freeze4/test_metrics.json`
- `model_server/classifier/runs/first-distilbert-freeze4/classification_report.json`

### Updated
- cleaned the final DistilBERT notebook evaluation cells so they run standalone from Drive
- `model_server/classifier/model_card.md`
- `docs/DECISIONS.md`
- `docs/BUILD_PLAN.md`

### Evidence
- test accuracy: `0.9534`
- test macro-F1: `0.9000`
- test weighted-F1: `0.9517`
- inference throughput: `70.2` examples/sec on `cuda`

### Design notes
- DistilBERT now has the missing temporal test evidence, making the comparison with the classical baseline fair on the same held-out split.
- DistilBERT is slightly stronger than the classical baseline on test macro-F1 (`0.9000` vs `0.8847`), but the classical baseline is far faster, so deployment choice still needs the LLM baseline and a latency/cost discussion.

## 2026-05-19 — DistilBERT test-evaluation path added

### Added
- `model_server/classifier/evaluate_distilbert.py`
- final test-evaluation cells in `notebooks/maintainers_copilot_week7_colab.ipynb`

### Updated
- `docs/COLAB_TRAINING.md`
- `model_server/classifier/runs/first-distilbert-freeze4/README.md`
- `model_server/classifier/model_card.md`
- `docs/BUILD_PLAN.md`

### Design notes
- The transformer track can now load the saved Drive model and evaluate the temporal `test.jsonl` split without retraining.
- Expected handoff files are `test_metrics.json` and `classification_report.json` under `model_server/classifier/runs/first-distilbert-freeze4/`.

## 2026-05-19 — Classical baseline Colab results added

### Added
- `model_server/classifier/runs/classical-tfidf-logreg/run_manifest.json`
- `model_server/classifier/runs/classical-tfidf-logreg/metrics.json`
- `model_server/classifier/runs/classical-tfidf-logreg/classification_report.json`

### Updated
- `notebooks/tfidf_logreg_baseline_colab.ipynb`
- `model_server/classifier/model_card.md`
- `docs/DECISIONS.md`
- `docs/BUILD_PLAN.md`

### Evidence
- validation accuracy: `0.7911`
- validation macro-F1: `0.7414`
- test accuracy: `0.9445`
- test macro-F1: `0.8847`
- vocabulary size: `50,000`

### Design notes
- The classical baseline is now a real comparison point, not just scaffolding.
- DistilBERT currently has validation evidence only, so the next fair comparison step is to evaluate DistilBERT on `test.jsonl` or add the LLM baseline and keep the comparison table explicit about which split each number came from.

## 2026-05-19 — Classifier track entrypoints clarified

### Renamed
- `model_server/classifier/train.py` → `model_server/classifier/train_distilbert.py`
- `model_server/classifier/classical_baseline.py` → `model_server/classifier/train_tfidf_logreg.py`

### Design notes
- The two classifier tracks now read as separate commands instead of generic training files.
- Colab workflow keeps the classical baseline in `notebooks/tfidf_logreg_baseline_colab.ipynb` rather than appending it into the DistilBERT run notebook.

## 2026-05-19 — Classical classifier baseline added

### Added
- `model_server/classifier/train_tfidf_logreg.py`
- `notebooks/tfidf_logreg_baseline_colab.ipynb`
- `model_server/classifier/io.py`
- `model_server/classifier/text.py`
- `model_server/classifier/runs/classical-tfidf-logreg/README.md`

### Updated
- shared classifier text preprocessing and dataset fingerprint helpers
- `model_server/classifier/train_distilbert.py` now reuses those helpers
- `model_server/classifier/model_card.md`
- `docs/DECISIONS.md`
- `docs/BUILD_PLAN.md`

### Design notes
- The comparison track now has its second implementation path: TF-IDF word n-grams plus balanced Logistic Regression.
- The baseline writes the same small evidence shape as the transformer track: manifest, metrics, and classification report.
- Local execution is pending because the current checkout does not have `scikit-learn` installed; the code path is ready for Colab or an environment with `model_server[train]` installed.

## 2026-05-19 — Corrected classifier splits and first run evidence committed

### Added
- `data/split_report.json`
- `model_server/classifier/runs/first-distilbert-freeze4/run_manifest.json`
- `model_server/classifier/runs/first-distilbert-freeze4/metrics.json`

### Updated
- corrected `data/train.jsonl`, `data/val.jsonl`, and `data/test.jsonl` from the Colab run
- `model_server/classifier/model_card.md`
- `docs/DECISIONS.md`
- `docs/BUILD_PLAN.md`
- `data/README.md`

### Evidence
- train: `10,012` examples, SHA-256 `24dd7452cbdff5f01158a9db52f3a63c4bc0a14e1984771a72144729e0973320`
- validation: `2,145` examples, SHA-256 `7888030eae31a4fd881d87a16c2c01d337d701094f11993c6483170b3583b797`
- test: `2,145` examples, SHA-256 `aa52b95e4479c495e352bfe23ee3eb3ed75a9ac77bce7c72026971ccb5f744de`
- first run validation macro-F1: `0.7422`
- first run validation accuracy: `0.8135`

### Design notes
- The local raw issue snapshot remains absent/empty because the user is working with limited disk space; the corrected splits and report are enough to continue classifier comparison work.
- The first DistilBERT run is now evidence-backed, but final model choice still requires the classical and LLM baselines on the same split.

## 2026-05-19 — Classifier run evidence landing zone added

### Added
- `model_server/classifier/runs/README.md`
- `model_server/classifier/runs/first-distilbert-freeze4/README.md`

### Updated
- `docs/COLAB_TRAINING.md`
- `data/README.md`

### Design notes
- Corrected Colab dataset files should land in `data/`; the small run evidence files should land beside the classifier code under `model_server/classifier/runs/`.
- Large model outputs remain outside Git: Drive is the temporary holding area until the project’s MinIO artifact path exists.

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
- real DistilBERT training entrypoint in `model_server/classifier/train_distilbert.py`
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
