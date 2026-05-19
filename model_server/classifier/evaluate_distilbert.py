"""Evaluate a saved DistilBERT classifier on a normalized JSONL split."""

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from model_server.classifier.io import fingerprint_jsonl, read_issue_examples
from model_server.classifier.training_config import LABEL_TO_ID

LABELS = tuple(LABEL_TO_ID.keys())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path("artifacts/classifier/first-distilbert-freeze4/model"),
        help="Directory containing the saved Hugging Face model/tokenizer.",
    )
    parser.add_argument("--test-path", type=Path, default=Path("data/test.jsonl"))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("model_server/classifier/runs/first-distilbert-freeze4"),
    )
    parser.add_argument("--batch-size", type=int, default=32)
    return parser.parse_args()


def evaluate_saved_model(
    model_dir: Path,
    test_path: Path,
    batch_size: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load the saved model and evaluate it on the test split."""
    dependencies = _load_eval_dependencies()
    AutoModelForSequenceClassification = dependencies["AutoModelForSequenceClassification"]
    AutoTokenizer = dependencies["AutoTokenizer"]
    torch = dependencies["torch"]
    accuracy_score = dependencies["accuracy_score"]
    classification_report = dependencies["classification_report"]
    confusion_matrix = dependencies["confusion_matrix"]
    f1_score = dependencies["f1_score"]

    if not model_dir.exists():
        raise FileNotFoundError(f"Missing saved model directory: {model_dir}")

    examples = read_issue_examples(test_path)
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    id_to_label = _id_to_label(model.config.id2label)
    predictions: list[str] = []
    if device.type == "cuda":
        torch.cuda.synchronize()
    started = perf_counter()
    with torch.no_grad():
        for start in range(0, len(examples), batch_size):
            batch = examples[start : start + batch_size]
            encoded = tokenizer(
                [example.text for example in batch],
                truncation=True,
                max_length=384,
                padding=True,
                return_tensors="pt",
            )
            encoded = {key: value.to(device) for key, value in encoded.items()}
            logits = model(**encoded).logits
            predicted_ids = torch.argmax(logits, dim=-1).detach().cpu().tolist()
            predictions.extend(id_to_label[predicted_id] for predicted_id in predicted_ids)

    if device.type == "cuda":
        torch.cuda.synchronize()
    predict_seconds = perf_counter() - started
    actual = [example.target for example in examples]
    report = classification_report(
        actual,
        predictions,
        labels=list(LABELS),
        output_dict=True,
        zero_division=0,
    )
    metrics = {
        "created_at": datetime.now(UTC).isoformat(),
        "split": split_name(test_path),
        "model_dir": str(model_dir),
        "dataset": asdict(fingerprint_jsonl(test_path)),
        "examples": len(examples),
        "accuracy": float(accuracy_score(actual, predictions)),
        "macro_f1": float(f1_score(actual, predictions, labels=list(LABELS), average="macro")),
        "weighted_f1": float(f1_score(actual, predictions, labels=list(LABELS), average="weighted")),
        "per_class_f1": {label: float(report[label]["f1-score"]) for label in LABELS},
        "confusion_matrix_labels": list(LABELS),
        "confusion_matrix": confusion_matrix(actual, predictions, labels=list(LABELS)).tolist(),
        "predict_seconds": predict_seconds,
        "examples_per_second": len(examples) / predict_seconds if predict_seconds else None,
        "device": str(device),
    }
    return metrics, report


def split_name(path: Path) -> str:
    return "test" if path.name == "test.jsonl" else path.stem


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _id_to_label(raw_id_to_label: dict[Any, str]) -> dict[int, str]:
    id_to_label = {int(key): value for key, value in raw_id_to_label.items()}
    expected = set(LABEL_TO_ID.values())
    if set(id_to_label) != expected:
        raise ValueError(f"Saved model labels do not match expected IDs: {id_to_label}")
    return id_to_label


def _load_eval_dependencies() -> dict[str, Any]:
    try:
        import torch
        from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError(
            "DistilBERT evaluation dependencies are missing. Install model-server train dependencies first."
        ) from exc

    return {
        "torch": torch,
        "AutoModelForSequenceClassification": AutoModelForSequenceClassification,
        "AutoTokenizer": AutoTokenizer,
        "accuracy_score": accuracy_score,
        "classification_report": classification_report,
        "confusion_matrix": confusion_matrix,
        "f1_score": f1_score,
    }


def main() -> None:
    args = parse_args()
    metrics, report = evaluate_saved_model(
        model_dir=args.model_dir,
        test_path=args.test_path,
        batch_size=args.batch_size,
    )
    write_json(args.output_dir / "test_metrics.json", metrics)
    write_json(args.output_dir / "classification_report.json", {split_name(args.test_path): report})
    print(json.dumps(metrics, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
