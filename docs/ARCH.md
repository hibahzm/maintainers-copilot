# Architecture

Maintainers Copilot is intentionally split into layers and services so each part can evolve without becoming a knot.

```text
HTTP clients
   │
   ▼
backend/app/api/schemas/ -> Pydantic HTTP contracts
   │
   ▼
backend/app/api/         -> routers + dependency injection only
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

1. Public request and response bodies are Pydantic models under `backend/app/api/schemas/`.
2. Routers receive services through FastAPI `Depends`; they do not construct repositories, clients, or services by hand.
3. Routers do not call the database directly.
4. Services do not raise HTTP exceptions.
5. Domain models under `backend/app/domain/` remain framework-agnostic and are not the same thing as transport schemas.
6. Repositories do not know about Redis, FastAPI, or model providers.
7. Redaction runs before logs and traces leave the process.
8. Vault becomes a startup dependency before any real secret is introduced.

## Backend flow

```text
request JSON
   │
   ▼
api/schemas       validate transport input
   │
   ▼
api routers       accept HTTP + inject services
   │
   ▼
services          run business workflows
   │
   ├── repositories  persist/query SQL
   └── infra         talk to external systems
   │
   ▼
domain models     represent core concepts
   │
   ▼
api/schemas       shape transport output
```
