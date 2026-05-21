# Security

## Principles already encoded in the scaffold

- secrets should come from Vault, not application env files
- logs and traces should pass through redaction first
- only the Vault development bootstrap token and ports are allowed in `.env.example`

## Startup secret contract

Before serving traffic, the API must connect to Vault and load one runtime secret bundle from:

- mount: `secret`
- path: `maintainers-copilot`

That bundle must contain:

- `database_password`
- `jwt_signing_key`
- `minio_access_key`
- `minio_secret_key`
- `llm_api_key`
- `tracing_api_key`

The local Compose stack initializes this bundle through the one-shot `vault-init` container. If Vault is unreachable, the bundle is missing, the payload is malformed, or any required value is empty, the API refuses to boot.

## Notebook secret hygiene

- Do not paste GitHub, Hugging Face, Weights & Biases, or OpenAI tokens directly into notebook cells.
- In Colab, provide credentials through the secrets UI or environment variables at runtime.
- If a token appears in a saved notebook, treat it as exposed and revoke it before continuing.
- For OpenAI baseline runs, provide `OPENAI_API_KEY` through Colab Secrets, `getpass`, or runtime environment variables only.

## Production vs notebook LLM keys

- Production app/runtime keys belong in Vault under `llm_api_key`.
- Notebook experiment keys do not go into Git or `.env`; use Colab Secrets or a temporary runtime prompt.
- The backend and model-server can receive the shipped-stack LLM key from the Vault-backed `llm_api_key` path, not from a hardcoded notebook value.

## Redaction patterns

Initial patterns live in `backend/app/infra/redaction.py` and currently cover:

- obvious `api_key=...` / `api-key: ...` style values
- bearer tokens

This list is deliberately small for now; each new pattern should be justified by a real leak path or test case.

Trace events must avoid raw issue/user text where possible and log metadata instead, such as character counts, route names, tool names, model names, durations, and citation counts. When a string is emitted, it passes through the redaction helper first.


## Model-server summarizer secret

The `/summarize` and `/rag-answer` tools are OpenAI-backed. The model-server may read `OPENAI_API_KEY` or `LLM_API_KEY` from its runtime environment for notebooks and one-off local smoke tests, but Compose runtime should read `llm_api_key` from Vault. Never commit API keys to `.env`, notebooks, run manifests, request logs, or eval outputs.
