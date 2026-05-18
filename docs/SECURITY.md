# Security

## Principles already encoded in the scaffold

- secrets should come from Vault, not application env files
- logs and traces should pass through redaction first
- only the Vault development root token is allowed in `.env.example`

## Redaction patterns

Initial patterns live in `backend/app/infra/redaction.py` and currently cover:

- obvious `api_key=...` / `api-key: ...` style values
- bearer tokens

This list is deliberately small for now; each new pattern should be justified by a real leak path or test case.
