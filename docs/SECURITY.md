# Security

## Principles already encoded in the scaffold

- secrets should come from Vault, not application env files
- logs and traces should pass through redaction first
- only the Vault development root token is allowed in `.env.example`

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

If Vault is unreachable, the bundle is missing, or the payload is malformed, the API refuses to boot.

## Notebook secret hygiene

- Do not paste GitHub, Hugging Face, Weights & Biases, or OpenAI tokens directly into notebook cells.
- In Colab, provide credentials through the secrets UI or environment variables at runtime.
- If a token appears in a saved notebook, treat it as exposed and revoke it before continuing.
- For OpenAI baseline runs, provide `OPENAI_API_KEY` through Colab Secrets, `getpass`, or runtime environment variables only.

## Production vs notebook LLM keys

- Production app/runtime keys belong in Vault under `llm_api_key`.
- Notebook experiment keys do not go into Git or `.env`; use Colab Secrets or a temporary runtime prompt.
- When the model server or backend later calls OpenAI in the shipped stack, it should receive the key from the Vault-backed settings path, not from a hardcoded notebook value.

## Redaction patterns

Initial patterns live in `backend/app/infra/redaction.py` and currently cover:

- obvious `api_key=...` / `api-key: ...` style values
- bearer tokens

This list is deliberately small for now; each new pattern should be justified by a real leak path or test case.
