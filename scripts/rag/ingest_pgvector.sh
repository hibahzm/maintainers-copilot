#!/usr/bin/env bash
set -euo pipefail

# Ingest generated RAG chunks into PostgreSQL/pgvector using the selected local
# embedding model. Defaults are safe for local development and pin CPU Torch.

CHUNKS_PATH="${CHUNKS_PATH:-data/rag/chunks/parent_child_chunks.jsonl}"
DATABASE_URL="${DATABASE_URL:-postgresql://copilot:copilot-dev-only@localhost:5432/copilot}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-intfloat/e5-small-v2}"
DEVICE="${DEVICE:-cpu}"
BATCH_SIZE="${BATCH_SIZE:-32}"
REPLACE_FLAG="${REPLACE_FLAG:---replace}"

if [[ ! -f "${CHUNKS_PATH}" ]]; then
  echo "Missing chunks file: ${CHUNKS_PATH}" >&2
  echo "Run: python -m scripts.rag.build_dev_corpus && python -m scripts.rag.chunk_parent_child" >&2
  exit 1
fi

uv run \
  --index-url https://download.pytorch.org/whl/cpu \
  --extra-index-url https://pypi.org/simple \
  --with "torch==2.5.1+cpu" \
  --with sentence-transformers \
  --with asyncpg \
  python -m scripts.rag.ingest_pgvector \
    --chunks-path "${CHUNKS_PATH}" \
    --database-url "${DATABASE_URL}" \
    --embedding-model "${EMBEDDING_MODEL}" \
    --device "${DEVICE}" \
    --batch-size "${BATCH_SIZE}" \
    ${REPLACE_FLAG}
