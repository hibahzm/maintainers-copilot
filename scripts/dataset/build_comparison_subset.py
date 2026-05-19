"""Build a small balanced classifier comparison subset from the temporal test split."""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from random import Random
from typing import Any

from scripts.dataset.constants import TARGET_LABELS
from scripts.dataset.io import read_jsonl, write_jsonl

DEFAULT_INPUT = Path("data/test.jsonl")
DEFAULT_OUTPUT = Path("data/test_200_balanced.jsonl")
DEFAULT_REPORT = Path("data/test_200_balanced_report.json")
DEFAULT_EXAMPLES_PER_LABEL = 50
DEFAULT_SEED = 42


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--examples-per-label", type=int, default=DEFAULT_EXAMPLES_PER_LABEL)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def build_subset(
    records: list[dict[str, Any]],
    examples_per_label: int,
    seed: int,
) -> list[dict[str, Any]]:
    """Sample the same number of examples per target label, deterministically."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        target = record.get("target")
        if target in TARGET_LABELS:
            grouped[target].append(record)

    missing = {
        label: examples_per_label - len(grouped[label])
        for label in TARGET_LABELS
        if len(grouped[label]) < examples_per_label
    }
    if missing:
        raise ValueError(
            f"Cannot build balanced subset with {examples_per_label} examples per label. "
            f"Missing counts: {missing}"
        )

    rng = Random(seed)
    selected: list[dict[str, Any]] = []
    for label in TARGET_LABELS:
        label_records = grouped[label][:]
        rng.shuffle(label_records)
        selected.extend(label_records[:examples_per_label])

    return sorted(selected, key=lambda record: (record.get("created_at") or "", record.get("id") or ""))


def build_report(
    input_path: Path,
    output_path: Path,
    records: list[dict[str, Any]],
    subset: list[dict[str, Any]],
    examples_per_label: int,
    seed: int,
) -> dict[str, Any]:
    return {
        "purpose": "small balanced comparison subset for evaluating DistilBERT, TF-IDF, and OpenAI on the same examples",
        "source_split": fingerprint_jsonl(input_path),
        "output_split": fingerprint_records(output_path, subset),
        "policy": {
            "source": str(input_path),
            "examples_per_label": examples_per_label,
            "seed": seed,
            "labels": list(TARGET_LABELS),
            "selection": "deterministic random sample within each class, then sorted by created_at for stable reading",
        },
        "source_label_counts": dict(sorted(Counter(record.get("target") for record in records).items())),
        "subset_label_counts": dict(sorted(Counter(record.get("target") for record in subset).items())),
        "date_range": date_range(subset),
        "note": "This file does not replace data/test.jsonl; it is only the cheap three-way comparison slice.",
    }


def date_range(records: list[dict[str, Any]]) -> dict[str, str | None]:
    dates = [record.get("created_at") for record in records if isinstance(record.get("created_at"), str)]
    if not dates:
        return {"oldest_created_at": None, "newest_created_at": None}
    return {"oldest_created_at": min(dates), "newest_created_at": max(dates)}


def fingerprint_jsonl(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    examples = 0
    with path.open("rb") as handle:
        for line in handle:
            if line.strip():
                examples += 1
            digest.update(line)
    return {"path": str(path), "sha256": digest.hexdigest(), "examples": examples}


def fingerprint_records(path: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    digest = hashlib.sha256()
    for record in records:
        digest.update(json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        digest.update(b"\n")
    return {"path": str(path), "sha256": digest.hexdigest(), "examples": len(records)}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main() -> None:
    args = parse_args()
    records = list(read_jsonl(args.input))
    subset = build_subset(records=records, examples_per_label=args.examples_per_label, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output, subset)
    report = build_report(
        input_path=args.input,
        output_path=args.output,
        records=records,
        subset=subset,
        examples_per_label=args.examples_per_label,
        seed=args.seed,
    )
    write_json(args.report, report)
    print(json.dumps(report["subset_label_counts"], sort_keys=True))
    print(f"Wrote {len(subset)} examples to {args.output}")


if __name__ == "__main__":
    main()
