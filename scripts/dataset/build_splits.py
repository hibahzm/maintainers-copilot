"""Normalize raw GitHub issues and build chronological, distribution-aware splits."""

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from random import Random
from typing import Any

from scripts.dataset.constants import LABEL_TO_TARGET, SOURCE_REPO, TARGET_LABELS
from scripts.dataset.io import read_jsonl, write_jsonl

DEFAULT_TEST_RATIO = 0.15
DEFAULT_VAL_RATIO = 0.15
DEFAULT_SPLIT_SEED = 42


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-input", type=Path, default=Path("data/raw_issues.jsonl"))
    parser.add_argument("--output-dir", type=Path, default=Path("data"))
    parser.add_argument("--test-ratio", type=float, default=DEFAULT_TEST_RATIO)
    parser.add_argument("--val-ratio", type=float, default=DEFAULT_VAL_RATIO)
    return parser.parse_args()


def build_dataset(
    raw_records: list[dict[str, Any]],
    test_ratio: float,
    val_ratio: float,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Normalize records, split them, and return a machine-readable report."""
    normalized, dropped = normalize_records(raw_records)
    ordered = sorted(normalized, key=_created_at)

    train_val, test = split_temporally(
        ordered,
        right_ratio=test_ratio,
        label="test",
    )
    train, val = split_stratified(
        train_val,
        right_ratio=val_ratio / (1 - test_ratio),
        seed=DEFAULT_SPLIT_SEED,
    )

    splits = {"train": train, "val": val, "test": test}
    report = build_report(splits=splits, dropped=dropped, total_raw=len(raw_records))
    assert_strict_test_recency(train=train, test=test)
    return splits, report


def normalize_records(
    raw_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], Counter[str]]:
    """Convert raw GitHub issues into single-label classifier examples."""
    normalized: list[dict[str, Any]] = []
    dropped: Counter[str] = Counter()

    for record in raw_records:
        label_names = {
            label["name"].casefold()
            for label in record.get("labels", [])
            if isinstance(label, dict) and isinstance(label.get("name"), str)
        }
        mapped_targets = {LABEL_TO_TARGET[label] for label in label_names if label in LABEL_TO_TARGET}

        if not mapped_targets:
            dropped["no_supported_target_label"] += 1
            continue
        if len(mapped_targets) > 1:
            dropped["ambiguous_multi_target_label"] += 1
            continue

        number = record.get("number")
        created_at = record.get("created_at")
        if not isinstance(number, int) or not isinstance(created_at, str):
            dropped["missing_required_fields"] += 1
            continue

        repo = record.get("repo_full_name", SOURCE_REPO)
        target = mapped_targets.pop()
        normalized.append(
            {
                "id": f"{repo}#{number}",
                "repo": repo,
                "number": number,
                "title": record.get("title") or "",
                "body": record.get("body") or "",
                "labels": sorted(label_names),
                "target": target,
                "created_at": created_at,
                "closed_at": record.get("closed_at"),
                "url": record.get("html_url"),
            }
        )

    return normalized, dropped


def split_temporally(
    records: list[dict[str, Any]],
    right_ratio: float,
    label: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Choose a chronological cutoff that best preserves the global label mix."""
    if not 0 < right_ratio < 1:
        raise ValueError("Split ratio must be between 0 and 1.")

    required_targets = set(TARGET_LABELS)
    overall_distribution = distribution(records)
    left_counts: Counter[str] = Counter()
    right_counts = counts(records)
    best: tuple[float, float, int] | None = None

    for index, record in enumerate(records[:-1], start=1):
        target = record["target"]
        left_counts[target] += 1
        right_counts[target] -= 1

        if not required_targets.issubset(left_counts):
            continue
        if not required_targets.issubset(
            label for label, count in right_counts.items() if count > 0
        ):
            continue

        right_size = len(records) - index
        size_error = abs((right_size / len(records)) - right_ratio)
        drift = distribution_distance(
            distribution_from_counts(right_counts, right_size),
            overall_distribution,
        )
        score = (size_error, drift, index)
        if best is None or score < best:
            best = score

    if best is None:
        raise ValueError(
            f"Could not create a temporal {label} split containing every target label. "
            "Fetch more issues or inspect label balance first."
        )

    _, _, cutoff = best
    return records[:cutoff], records[cutoff:]


def split_stratified(
    records: list[dict[str, Any]],
    right_ratio: float,
    seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build a deterministic stratified split inside the older train/validation pool."""
    if not 0 < right_ratio < 1:
        raise ValueError("Split ratio must be between 0 and 1.")

    grouped: dict[str, list[dict[str, Any]]] = {label: [] for label in TARGET_LABELS}
    for record in records:
        grouped[record["target"]].append(record)

    if any(len(grouped[label]) < 2 for label in TARGET_LABELS):
        raise ValueError("Every target label needs at least two examples for stratified validation.")

    rng = Random(seed)
    train: list[dict[str, Any]] = []
    val: list[dict[str, Any]] = []

    for label in TARGET_LABELS:
        group = grouped[label][:]
        rng.shuffle(group)
        val_count = max(1, round(len(group) * right_ratio))
        if val_count >= len(group):
            val_count = len(group) - 1
        val.extend(group[:val_count])
        train.extend(group[val_count:])

    return sorted(train, key=_created_at), sorted(val, key=_created_at)


def build_report(
    splits: dict[str, list[dict[str, Any]]],
    dropped: Counter[str],
    total_raw: int,
) -> dict[str, Any]:
    """Create the split/count report required by the build plan."""
    return {
        "source_repo": SOURCE_REPO,
        "target_labels": list(TARGET_LABELS),
        "split_policy": {
            "test": "strictly newer temporal holdout",
            "validation": "deterministic stratified split inside the older train/validation pool",
            "seed": DEFAULT_SPLIT_SEED,
            "temporal_holdout_priority": "closest target size first, distribution drift second",
        },
        "total_raw_records": total_raw,
        "total_normalized_records": sum(len(records) for records in splits.values()),
        "dropped_records": dict(sorted(dropped.items())),
        "splits": {
            name: {
                "count": len(records),
                "label_counts": dict(sorted(counts(records).items())),
                "date_range": date_range(records),
            }
            for name, records in splits.items()
        },
    }


def write_outputs(
    output_dir: Path,
    splits: dict[str, list[dict[str, Any]]],
    report: dict[str, Any],
) -> None:
    """Persist normalized split files and the report."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, records in splits.items():
        write_jsonl(output_dir / f"{name}.jsonl", records)

    with (output_dir / "split_report.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")


def assert_strict_test_recency(
    train: list[dict[str, Any]],
    test: list[dict[str, Any]],
) -> None:
    """Enforce the assignment rule that test examples are newer than train examples."""
    if _created_at(train[-1]) >= _created_at(test[0]):
        raise AssertionError("The test split is not strictly newer than the training split.")


def counts(records: list[dict[str, Any]]) -> Counter[str]:
    return Counter(record["target"] for record in records)


def distribution(records: list[dict[str, Any]]) -> dict[str, float]:
    record_counts = counts(records)
    total = sum(record_counts.values())
    return distribution_from_counts(record_counts, total)


def distribution_from_counts(record_counts: Counter[str], total: int) -> dict[str, float]:
    if total == 0:
        return {}
    return {label: record_counts[label] / total for label in TARGET_LABELS}


def distribution_distance(
    candidate: dict[str, float],
    reference: dict[str, float],
) -> float:
    return sum(abs(candidate.get(label, 0.0) - reference.get(label, 0.0)) for label in TARGET_LABELS)


def date_range(records: list[dict[str, Any]]) -> dict[str, str]:
    return {
        "oldest_created_at": records[0]["created_at"],
        "newest_created_at": records[-1]["created_at"],
    }


def _created_at(record: dict[str, Any]) -> datetime:
    return datetime.fromisoformat(record["created_at"].replace("Z", "+00:00"))


def main() -> None:
    args = parse_args()
    raw_records = list(read_jsonl(args.raw_input))
    splits, report = build_dataset(
        raw_records=raw_records,
        test_ratio=args.test_ratio,
        val_ratio=args.val_ratio,
    )
    write_outputs(output_dir=args.output_dir, splits=splits, report=report)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
