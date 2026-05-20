"""Check committed evaluation result files against lightweight thresholds.

This is intentionally offline: CI should fail if the checked-in evidence regresses,
but it should not need a model server, GPU, OpenAI key, or pgvector index.
Live eval commands remain in the runbook for release verification.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--thresholds", type=Path, default=Path("evals/eval_thresholds.yaml"))
    parser.add_argument(
        "--classification-results",
        type=Path,
        default=Path("evals/classification_eval_results.json"),
    )
    parser.add_argument(
        "--rag-results",
        type=Path,
        default=Path("evals/rag_query_transform_results.json"),
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing eval result file: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected object in {path}")
    return data


def threshold(text: str, key: str) -> float:
    match = re.search(rf"^\s*{re.escape(key)}:\s*([0-9]+(?:\.[0-9]+)?)\s*$", text, re.M)
    if not match:
        raise ValueError(f"Missing threshold key: {key}")
    return float(match.group(1))


def metric(data: dict[str, Any], key: str, *, path: Path) -> float:
    value = data.get("metrics", {}).get(key)
    if not isinstance(value, int | float):
        raise ValueError(f"Missing numeric metric {key!r} in {path}")
    return float(value)


def check_at_least(name: str, actual: float, minimum: float) -> None:
    if actual < minimum:
        raise AssertionError(f"{name}={actual:.4f} is below required minimum {minimum:.4f}")
    print(f"ok: {name}={actual:.4f} >= {minimum:.4f}")


def main() -> None:
    args = parse_args()
    thresholds_text = args.thresholds.read_text(encoding="utf-8")

    classification = load_json(args.classification_results)
    rag = load_json(args.rag_results)

    check_at_least(
        "classification.macro_f1",
        metric(classification, "macro_f1", path=args.classification_results),
        threshold(thresholds_text, "macro_f1_min"),
    )
    check_at_least(
        "rag.recall_at_5",
        metric(rag, "recall_at_5", path=args.rag_results),
        threshold(thresholds_text, "retrieval_recall_at_5_min"),
    )


if __name__ == "__main__":
    main()
