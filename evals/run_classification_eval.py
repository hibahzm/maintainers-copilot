"""Run the hand-curated classification golden set against a classifier endpoint."""

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LABELS = ("bug", "feature", "docs", "question")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden-path", type=Path, default=Path("evals/golden_classification.json"))
    parser.add_argument("--endpoint", default="http://localhost:8001/classify")
    parser.add_argument("--output", type=Path, default=Path("evals/classification_eval_results.json"))
    return parser.parse_args()


def load_golden(path: Path) -> list[dict[str, Any]]:
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list) or not records:
        raise ValueError(f"Golden set must be a non-empty list: {path}")
    seen: set[str] = set()
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"Golden record {index} must be an object.")
        record_id = record.get("id")
        expected = record.get("expected_label")
        if not isinstance(record_id, str) or not record_id:
            raise ValueError(f"Golden record {index} is missing a string id.")
        if record_id in seen:
            raise ValueError(f"Duplicate golden id: {record_id}")
        seen.add(record_id)
        if expected not in LABELS:
            raise ValueError(f"Golden record {record_id} has unsupported expected_label: {expected!r}")
        if not isinstance(record.get("title"), str) or not record["title"].strip():
            raise ValueError(f"Golden record {record_id} is missing a title.")
        if not isinstance(record.get("body"), str):
            raise ValueError(f"Golden record {record_id} is missing a string body.")
    return records


def request_prediction(endpoint: str, record: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps({"title": record["title"], "body": record["body"]}).encode("utf-8")
    request = Request(endpoint, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Classifier endpoint returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach classifier endpoint {endpoint!r}: {exc}") from exc
    if not isinstance(result, dict) or result.get("label") not in LABELS:
        raise RuntimeError(f"Classifier endpoint returned unsupported payload: {result!r}")
    return result


def compute_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    correct = sum(1 for row in rows if row["expected_label"] == row["predicted_label"])
    per_label: dict[str, dict[str, float]] = {}
    for label in LABELS:
        tp = sum(1 for row in rows if row["expected_label"] == label and row["predicted_label"] == label)
        fp = sum(1 for row in rows if row["expected_label"] != label and row["predicted_label"] == label)
        fn = sum(1 for row in rows if row["expected_label"] == label and row["predicted_label"] != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_label[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": sum(1 for row in rows if row["expected_label"] == label),
        }
    return {
        "examples": total,
        "accuracy": correct / total if total else 0.0,
        "macro_f1": sum(per_label[label]["f1"] for label in LABELS) / len(LABELS),
        "label_counts": dict(Counter(row["expected_label"] for row in rows)),
        "per_label": per_label,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    golden = load_golden(args.golden_path)
    rows: list[dict[str, Any]] = []
    for record in golden:
        prediction = request_prediction(args.endpoint, record)
        rows.append(
            {
                "id": record["id"],
                "expected_label": record["expected_label"],
                "predicted_label": prediction["label"],
                "confidence": prediction.get("confidence"),
                "correct": record["expected_label"] == prediction["label"],
            }
        )
    output = {
        "endpoint": args.endpoint,
        "golden_path": str(args.golden_path),
        "metrics": compute_metrics(rows),
        "predictions": rows,
    }
    write_json(args.output, output)
    print(json.dumps(output["metrics"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
