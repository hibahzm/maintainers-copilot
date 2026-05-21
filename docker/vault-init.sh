#!/bin/sh
set -eu

VAULT_SECRET_PATH="${VAULT_SECRET_PATH:-maintainers-copilot}"
VAULT_MOUNT_POINT="${VAULT_MOUNT_POINT:-secret}"

echo "Waiting for Vault at ${VAULT_ADDR}..."
until vault status >/dev/null 2>&1; do
  sleep 1
done

vault secrets enable -path="${VAULT_MOUNT_POINT}" kv-v2 >/dev/null 2>&1 || true

vault kv put "${VAULT_MOUNT_POINT}/${VAULT_SECRET_PATH}" \
  database_password="${POSTGRES_PASSWORD:-copilot-dev-only}" \
  jwt_signing_key="${JWT_SIGNING_KEY:-dev-only-jwt-signing-key}" \
  minio_access_key="${MINIO_ROOT_USER:-minioadmin}" \
  minio_secret_key="${MINIO_ROOT_PASSWORD:-minioadmin-dev-only}" \
  llm_api_key="${OPENAI_API_KEY:-${LLM_API_KEY:-}}" \
  tracing_api_key="${TRACING_API_KEY:-${LANGFUSE_SECRET_KEY:-dev-only-tracing-key}}" \
  langfuse_public_key="${LANGFUSE_PUBLIC_KEY:-dev-only-langfuse-public-key}" \
  langfuse_secret_key="${LANGFUSE_SECRET_KEY:-${TRACING_API_KEY:-dev-only-langfuse-secret-key}}"

echo "Vault secret bundle initialized at ${VAULT_MOUNT_POINT}/${VAULT_SECRET_PATH}."
