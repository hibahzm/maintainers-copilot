"""Small JSONL helpers shared by dataset scripts."""

import json
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """Yield one decoded object per non-empty JSONL line."""
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


def write_jsonl(path: Path, records: Iterable[Mapping[str, Any]]) -> None:
    """Write records as stable, UTF-8 JSONL."""
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
