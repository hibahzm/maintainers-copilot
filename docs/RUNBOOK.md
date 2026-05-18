# Runbook

## Current stage

Foundation work has started. Docker Compose now names the full required stack, Alembic has a baseline migration, the API treats Vault as a startup dependency, and every request now gets a request ID plus trace ID. The next coding pass should build the dataset pipeline.

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
