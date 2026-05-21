# Runbook

## Current stage

Foundation work has started. Docker Compose now names the full required stack, Alembic has a baseline migration, Vault is initialized by a one-shot `vault-init` container, the API treats Vault as a startup dependency, and every request now gets a request ID plus trace ID.

## Vault startup contract

The local Compose stack starts Vault in dev mode, then runs `vault-init` once to create a KV v2 secret bundle at:

```text
secret/data/maintainers-copilot
```

Required keys:

```text
database_password
jwt_signing_key
minio_access_key
minio_secret_key
llm_api_key
tracing_api_key
```

`vault-init` seeds the bundle from runtime environment variables. Keep `.env` limited to the Vault bootstrap token and ports. For real LLM smoke tests, export the key only for the command that starts/updates Vault:

```bash
export OPENAI_API_KEY="..."
docker compose up vault vault-init
```

At startup the API:

1. checks Vault health,
2. loads the bundle,
3. validates that every required key exists,
4. refuses to boot if any of those steps fail.

The backend uses `jwt_signing_key` and `llm_api_key` from this validated runtime bundle. The model-server still accepts direct `OPENAI_API_KEY` / `LLM_API_KEY` for notebooks and one-off smoke tests, but in Compose it can read `llm_api_key` from the same Vault bundle.

The API refuses to boot if any required Vault secret is empty. The model-server refuses to boot if the classifier artifact directory is missing, if its SHA-256 differs from the expected fingerprint, or if no LLM key is available for the LLM-backed summarization/RAG-answer tools.

Inspect the seeded bundle:

```bash
docker compose exec vault vault kv get secret/maintainers-copilot
```

## Request tracing contract

The API owns two request-level identifiers from the first user-facing hop:

- `X-Request-ID` — the ID shown back to users when something fails
- `X-Trace-ID` — the ID shared by structured logs and future tracing spans

If a caller does not provide them, the API creates both and returns them in the response headers. Later LLM, tool, and retrieval spans attach beneath the same trace ID.

The backend also emits redacted JSON trace events to stdout for the main product path:

- `chat.respond.*`
- `agent.*`
- `llm.responses.*`
- `chat_tools.*`
- `model_server.tool.*`
- `rag.*`

Inspect them through Docker logs:

```bash
docker compose logs -f api
```

These local trace events are provider-neutral. The accepted external trace UI choice remains Langfuse, but the shipped code does not require a Langfuse SDK to boot.

## Future sections

- local startup
- secret bootstrap
- migrations
- health checks
- backup / restore
- common failure modes

## First fine-tuning handoff

Use `docs/COLAB_TRAINING.md` for the first notebook run. If local disk is limited, Colab may host both the generated dataset and the model artifacts; the important rule is still that repository code owns the pipeline.


## Classifier serving

The selected issue classifier is DistilBERT run `first-distilbert-freeze4`. The model server exposes it at:

```text
POST /classify
```

Runtime requirement:

```text
CLASSIFIER_MODEL_DIR=artifacts/classifier/first-distilbert-freeze4/model
```

That directory must contain the saved Hugging Face tokenizer/model files from Colab or the future MinIO artifact flow. Do not commit the model weights to Git.

Record the model artifact fingerprint before or after evaluation:

```bash
python -m scripts.artifacts.fingerprint_model artifacts/classifier/first-distilbert-freeze4/model
```

The top-level `sha256` identifies the full model directory for eval evidence and future MinIO manifests.

For Docker Compose, the host `./artifacts` directory is mounted read-only into the model-server container at `/app/artifacts`, so the container uses:

```text
CLASSIFIER_MODEL_DIR=/app/artifacts/classifier/first-distilbert-freeze4/model
```

Example request:

```json
{
  "title": "BUG: read_csv crashes on empty file",
  "body": "read_csv raises an unexpected exception when..."
}
```

The backend API proxies this through `POST /classifier`, using `MODEL_SERVER_URL` to locate the model server.

Docker smoke command:

```bash
curl -X POST http://localhost:8001/classify \
  -H "Content-Type: application/json" \
  -d '{"title":"BUG: read_csv crashes on empty file","body":"read_csv raises an unexpected exception when the CSV has no rows."}'
```

Observed smoke result on 2026-05-19:

```text
label=bug
confidence=0.9649578332901001
model_artifact_sha256=45790f41e45d707aada1b76e87e4b6919e51ea357c40bc1f30a444fe34a6f67a
```


## NER serving

The model server exposes a rule-based code-shaped entity extractor at:

```text
POST /ner
```

Example request:

```bash
curl -X POST http://localhost:8001/ner \
  -H "Content-Type: application/json" \
  -d '{"title":"BUG: read_csv crashes on pandas 2.2","body":"ValueError from pandas/io/parsers.py on Windows for CSV."}'
```

The tool extracts maintainer-oriented entities such as functions, dotted symbols, package/version mentions, exceptions, file paths, URLs, operating systems, and file types.

## Summarizer serving

The model server exposes an OpenAI-backed structured summarizer at:

```text
POST /summarize
```

Default model:

```text
OPENAI_SUMMARIZER_MODEL=gpt-4o-mini
```

Secrets rule: do not put the API key in Git. Local smoke tests may export `OPENAI_API_KEY`; production should inject it from Vault/secrets into the model-server runtime.

Example request:

```bash
curl -X POST http://localhost:8001/summarize \
  -H "Content-Type: application/json" \
  -d '{"title":"BUG: read_csv crashes on empty file","body":"read_csv raises an unexpected exception when the CSV has no rows."}'
```

Expected response shape includes `summary`, `key_points`, `affected_entities`, `maintainer_next_steps`, `risk_level`, `model_name`, `provider`, and `response_id`.
