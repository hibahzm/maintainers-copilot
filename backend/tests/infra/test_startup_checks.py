from pathlib import Path

import pytest
from pydantic import SecretStr

from app.core.config import RuntimeSecrets, Settings
from app.infra.startup_checks import (
    assert_eval_thresholds_enabled,
    assert_runtime_secrets_non_empty,
    assert_tracing_configured,
)
from app.infra.vault import VaultStartupError


def runtime_secrets(*, tracing_key: str = "trace-key") -> RuntimeSecrets:
    return RuntimeSecrets(
        database_password=SecretStr("db"),
        jwt_signing_key=SecretStr("jwt"),
        minio_access_key=SecretStr("minio"),
        minio_secret_key=SecretStr("minio-secret"),
        llm_api_key=SecretStr("llm"),
        tracing_api_key=SecretStr(tracing_key),
    )


def test_tracing_config_accepts_langfuse_with_key():
    assert_tracing_configured(Settings(), runtime_secrets())


def test_runtime_secrets_reject_empty_llm_key():
    secrets = runtime_secrets()
    secrets.llm_api_key = SecretStr("")

    with pytest.raises(VaultStartupError):
        assert_runtime_secrets_non_empty(secrets)


def test_tracing_config_rejects_missing_key():
    with pytest.raises(VaultStartupError):
        assert_tracing_configured(Settings(), runtime_secrets(tracing_key=""))


def test_eval_thresholds_must_be_positive(tmp_path: Path):
    thresholds = tmp_path / "thresholds.yaml"
    thresholds.write_text(
        "classification:\n"
        "  macro_f1_min: 0.80\n"
        "rag:\n"
        "  answer_faithfulness_min: 0.85\n"
        "  retrieval_recall_at_5_min: 0.80\n",
        encoding="utf-8",
    )

    assert_eval_thresholds_enabled(thresholds)


def test_eval_thresholds_reject_disabled_values(tmp_path: Path):
    thresholds = tmp_path / "thresholds.yaml"
    thresholds.write_text(
        "classification:\n"
        "  macro_f1_min: 0\n"
        "rag:\n"
        "  answer_faithfulness_min: 0.85\n"
        "  retrieval_recall_at_5_min: 0.80\n",
        encoding="utf-8",
    )

    with pytest.raises(VaultStartupError):
        assert_eval_thresholds_enabled(thresholds)
