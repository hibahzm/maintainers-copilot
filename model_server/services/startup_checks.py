"""Model-server startup invariants."""

from __future__ import annotations

import os
from pathlib import Path

from model_server.services.artifacts import fingerprint_directory
from model_server.services.classifier import classifier_model_dir
from model_server.services.runtime_secrets import runtime_secret_value

DEFAULT_CLASSIFIER_EXPECTED_SHA256 = "45790f41e45d707aada1b76e87e4b6919e51ea357c40bc1f30a444fe34a6f67a"


class ModelServerStartupError(RuntimeError):
    """Raised when the model server cannot safely serve inference."""


def assert_classifier_artifact_ready(
    *,
    model_dir: Path | None = None,
    expected_sha256: str | None = None,
) -> None:
    model_dir = model_dir or classifier_model_dir()
    expected_sha256 = expected_sha256 or os.getenv(
        "CLASSIFIER_EXPECTED_SHA256",
        DEFAULT_CLASSIFIER_EXPECTED_SHA256,
    )
    if not model_dir.exists():
        raise ModelServerStartupError(f"Missing classifier model directory: {model_dir}")
    actual_sha256 = fingerprint_directory(model_dir).sha256
    if actual_sha256 != expected_sha256:
        raise ModelServerStartupError(
            "Classifier model artifact SHA-256 mismatch: "
            f"expected {expected_sha256}, got {actual_sha256}"
        )


def assert_llm_secret_available() -> None:
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY") or runtime_secret_value("llm_api_key")
    if not api_key or not api_key.strip():
        raise ModelServerStartupError("Missing LLM API key for summarization/RAG answer tools.")
