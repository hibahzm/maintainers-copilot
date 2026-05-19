"""Artifact fingerprint helpers shared by model-server services and scripts."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path

_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class FileFingerprint:
    path: str
    bytes: int
    sha256: str


@dataclass(frozen=True)
class DirectoryFingerprint:
    path: str
    sha256: str
    files: list[FileFingerprint]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint_directory(path: Path) -> DirectoryFingerprint:
    """Create a deterministic SHA-256 fingerprint for a model directory.

    The directory digest is derived from each file's relative path, size, and
    file SHA. It does not store file contents, so it is safe to commit in small
    manifests/eval results.
    """
    if not path.exists():
        raise FileNotFoundError(f"Missing artifact directory: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"Artifact path is not a directory: {path}")

    files: list[FileFingerprint] = []
    for file_path in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        relative_path = file_path.relative_to(path).as_posix()
        files.append(
            FileFingerprint(
                path=relative_path,
                bytes=file_path.stat().st_size,
                sha256=sha256_file(file_path),
            )
        )

    digest = hashlib.sha256()
    for file_fingerprint in files:
        digest.update(file_fingerprint.path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(file_fingerprint.bytes).encode("ascii"))
        digest.update(b"\0")
        digest.update(file_fingerprint.sha256.encode("ascii"))
        digest.update(b"\n")

    return DirectoryFingerprint(path=str(path), sha256=digest.hexdigest(), files=files)


def fingerprint_asdict(fingerprint: DirectoryFingerprint) -> dict[str, object]:
    return asdict(fingerprint)
