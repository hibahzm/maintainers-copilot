#!/usr/bin/env bash
set -euo pipefail

uv run --with minio python -m scripts.storage.bootstrap_minio "$@"
