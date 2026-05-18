# Architecture

Maintainers Copilot is intentionally split into layers and services so each part can evolve without becoming a knot.

```text
HTTP clients
   │
   ▼
backend/app/api/        -> request/response shaping only
   │
   ▼
backend/app/services/   -> business workflows
   │
   ├── backend/app/repositories/ -> SQL persistence
   └── backend/app/infra/        -> external systems: Vault, Redis, MinIO, LLMs, tracing
```

## Service boundaries

- `backend/` owns user-facing HTTP APIs, orchestration, persistence access, and security policy.
- `model_server/` owns ML inference APIs so model runtime concerns do not pollute the main API process.
- `chatbot/` is a maintainer-facing UI.
- `widget/` is a public-facing embeddable client.
- `demo/host/` proves the widget can live inside a plain host page.

## Layer rules

1. Routers do not call the database directly.
2. Services do not raise HTTP exceptions.
3. Repositories do not know about Redis, FastAPI, or model providers.
4. Redaction runs before logs and traces leave the process.
5. Vault becomes a startup dependency before any real secret is introduced.
