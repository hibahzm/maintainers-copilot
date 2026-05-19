from pathlib import Path

from model_server.services.artifacts import fingerprint_directory, sha256_file


def test_fingerprint_directory_is_deterministic(tmp_path: Path):
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    (model_dir / "b.txt").write_text("beta")
    (model_dir / "a.txt").write_text("alpha")

    first = fingerprint_directory(model_dir)
    second = fingerprint_directory(model_dir)

    assert first.sha256 == second.sha256
    assert [file.path for file in first.files] == ["a.txt", "b.txt"]
    assert first.files[0].sha256 == sha256_file(model_dir / "a.txt")


def test_fingerprint_directory_changes_when_file_changes(tmp_path: Path):
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    path = model_dir / "config.json"
    path.write_text('{"version": 1}')
    before = fingerprint_directory(model_dir).sha256

    path.write_text('{"version": 2}')
    after = fingerprint_directory(model_dir).sha256

    assert before != after
