# Runbook

## Current stage

Foundation work has started. Docker Compose now names the full required stack, Alembic has a baseline migration, and the API code now treats Vault as a startup dependency. The next coding pass should add request/trace plumbing before dataset work begins.

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

## Future sections

- local startup
- secret bootstrap
- migrations
- health checks
- backup / restore
- common failure modes
