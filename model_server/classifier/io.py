"""Small dataset helpers shared by classifier experiments."""

import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from model_server.classifier.text import compose_issue_text
from model_server.classifier.training_config import LABEL_TO_ID


@dataclass(frozen=True, slots=True)
class DatasetFingerprint:
    """Stable facts that let a future model card recover exact dataset inputs."""

    path: str
    sha256: str
    examples: int


@dataclass(frozen=True, slots=True)
class IssueExample:
    """One normalized issue-classification example."""

    text: str
    target: str
    identifier: str | None = None


def fingerprint_jsonl(path: Path) -> DatasetFingerprint:
    """Hash and count a non-empty JSONL dataset split."""
    if not path.exists():
        raise FileNotFoundError(f"Missing dataset split: {path}")

    digest = hashlib.sha256()
    examples = 0
    with path.open("rb") as handle:
        for line in handle:
            if line.strip():
                examples += 1
            digest.update(line)

    if examples == 0:
        raise ValueError(f"Dataset split is empty: {path}")

    return DatasetFingerprint(path=str(path), sha256=digest.hexdigest(), examples=examples)


def read_issue_examples(path: Path) -> list[IssueExample]:
    """Load a normalized classifier split into text/target examples."""
    return [
        IssueExample(
            text=compose_issue_text(title=record.get("title"), body=record.get("body")),
            target=_target_from_record(record=record, path=path, line_number=line_number),
            identifier=record.get("id") if isinstance(record.get("id"), str) else None,
        )
        for line_number, record in enumerate(_read_jsonl(path), start=1)
    ]


def _read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing dataset split: {path}")

    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} of {path}.") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"Expected an object on line {line_number} of {path}.")
            yield payload


def _target_from_record(record: dict[str, Any], path: Path, line_number: int) -> str:
    target = record.get("target")
    if not isinstance(target, str):
        raise ValueError(f"Missing string target on line {line_number} of {path}.")
    if target not in LABEL_TO_ID:
        raise ValueError(f"Unsupported target {target!r} on line {line_number} of {path}.")
    return target
