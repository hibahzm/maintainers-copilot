"""Startup invariants that must hold before the API serves traffic."""

from __future__ import annotations

import re
from pathlib import Path

from app.core.config import RuntimeSecrets, Settings
from app.infra.vault import VaultStartupError


def assert_tracing_configured(settings: Settings, secrets: RuntimeSecrets) -> None:
    """Fail fast when the selected tracing backend is missing required secret material."""
    backend = settings.tracing_backend.strip().lower()
    if backend != "langfuse":
        raise VaultStartupError(f"Unsupported tracing backend: {settings.tracing_backend!r}")
    if not settings.tracing_host.strip():
        raise VaultStartupError("Tracing backend host is not configured.")
    if not secrets.tracing_api_key.get_secret_value().strip():
        raise VaultStartupError("Tracing backend API key is missing from Vault.")


def assert_runtime_secrets_non_empty(secrets: RuntimeSecrets) -> None:
    """Fail fast if Vault returned an empty value for a required runtime secret."""
    for field_name in (
        "database_password",
        "jwt_signing_key",
        "minio_access_key",
        "minio_secret_key",
        "llm_api_key",
        "tracing_api_key",
    ):
        value = getattr(secrets, field_name).get_secret_value()
        if not value.strip():
            raise VaultStartupError(f"Vault runtime secret is empty: {field_name}")


def assert_eval_thresholds_enabled(path: Path) -> None:
    """Fail fast if committed eval thresholds are absent, zero, or disabled."""
    if not path.exists():
        raise VaultStartupError(f"Eval thresholds file is missing: {path}")
    text = path.read_text(encoding="utf-8")
    required_keys = (
        "macro_f1_min",
        "answer_faithfulness_min",
        "retrieval_recall_at_5_min",
    )
    for key in required_keys:
        value = _threshold_value(text, key)
        if value <= 0:
            raise VaultStartupError(f"Eval threshold {key} must be greater than zero.")


def _threshold_value(text: str, key: str) -> float:
    match = re.search(rf"^\s*{re.escape(key)}:\s*([0-9]+(?:\.[0-9]+)?)\s*$", text, re.M)
    if not match:
        raise VaultStartupError(f"Eval threshold {key} is missing.")
    return float(match.group(1))
