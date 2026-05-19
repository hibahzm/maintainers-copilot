# Runbook

## Current stage

Foundation work has started. Docker Compose now names the full required stack, Alembic has a baseline migration, the API treats Vault as a startup dependency, every request now gets a request ID plus trace ID, and the first fine-tuning path has a written Colab notebook workflow. The next execution pass can happen entirely in Colab: fetch, split, inspect, then train.

## Vault startup contract

The API expects a KV v2 secret bundle at:

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

At startup the API:

1. checks Vault health,
2. loads the bundle,
3. validates that every required key exists,
4. refuses to boot if any of those steps fail.

## Request tracing contract

The API owns two request-level identifiers from the first user-facing hop:

- `X-Request-ID` — the ID shown back to users when something fails
- `X-Trace-ID` — the ID shared by structured logs and future tracing spans

If a caller does not provide them, the API creates both and returns them in the response headers. Later LLM, tool, and retrieval spans attach beneath the same trace ID.

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

Example request:

```json
{
  "title": "BUG: read_csv crashes on empty file",
  "body": "read_csv raises an unexpected exception when..."
}
```

The backend API proxies this through `POST /classifier`, using `MODEL_SERVER_URL` to locate the model server.
