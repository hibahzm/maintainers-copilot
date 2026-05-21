from pathlib import Path

import pytest

from model_server.services.startup_checks import (
    ModelServerStartupError,
    assert_classifier_artifact_ready,
)


def test_classifier_artifact_ready_rejects_missing_directory(tmp_path: Path):
    with pytest.raises(ModelServerStartupError):
        assert_classifier_artifact_ready(model_dir=tmp_path / "missing", expected_sha256="abc")


def test_classifier_artifact_ready_rejects_sha_mismatch(tmp_path: Path):
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    (model_dir / "config.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ModelServerStartupError):
        assert_classifier_artifact_ready(model_dir=model_dir, expected_sha256="not-the-sha")
