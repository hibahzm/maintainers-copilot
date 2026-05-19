"""Train and evaluate the classical TF-IDF + Logistic Regression baseline."""

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from model_server.classifier.io import fingerprint_jsonl, read_issue_examples
from model_server.classifier.training_config import LABEL_TO_ID

DEFAULT_RUN_NAME = "classical-tfidf-logreg"
LABELS = tuple(LABEL_TO_ID.keys())


@dataclass(frozen=True, slots=True)
class ClassicalBaselineConfig:
    """A compact, reproducible classical baseline recipe."""

    run_name: str = DEFAULT_RUN_NAME
    model_family: str = "tfidf_logistic_regression"
    analyzer: str = "word"
    ngram_min: int = 1
    ngram_max: int = 2
    max_features: int = 50_000
    min_df: int = 2
    sublinear_tf: bool = True
    lowercase: bool = True
    strip_accents: str = "unicode"
    logistic_regression_max_iter: int = 1_000
    logistic_regression_c: float = 4.0
    class_weight: str = "balanced"
    random_state: int = 42


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-path", type=Path, default=Path("data/train.jsonl"))
    parser.add_argument("--val-path", type=Path, default=Path("data/val.jsonl"))
    parser.add_argument("--test-path", type=Path, default=Path("data/test.jsonl"))
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=Path("model_server/classifier/runs") / DEFAULT_RUN_NAME,
    )
    parser.add_argument("--run-name", default=DEFAULT_RUN_NAME)
    return parser.parse_args()


def build_run_manifest(
    config: ClassicalBaselineConfig,
    train_path: Path,
    val_path: Path,
    test_path: Path,
) -> dict[str, Any]:
    """Capture exact inputs and hyperparameters before fitting."""
    fingerprints = {
        "train": fingerprint_jsonl(train_path),
        "val": fingerprint_jsonl(val_path),
        "test": fingerprint_jsonl(test_path),
    }
    return {
        "created_at": datetime.now(UTC).isoformat(),
        "experiment": "classical_baseline",
        "config": asdict(config),
        "labels": LABEL_TO_ID,
        "dataset": {name: asdict(fingerprint) for name, fingerprint in fingerprints.items()},
        "artifact_policy": "commit small metrics/manifests only; do not commit binary model artifacts",
    }


def train_and_evaluate(
    config: ClassicalBaselineConfig,
    train_path: Path,
    val_path: Path,
    test_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fit the baseline and return metrics plus detailed reports."""
    dependencies = _load_baseline_dependencies()
    LogisticRegression = dependencies["LogisticRegression"]
    Pipeline = dependencies["Pipeline"]
    TfidfVectorizer = dependencies["TfidfVectorizer"]

    train_examples = read_issue_examples(train_path)
    val_examples = read_issue_examples(val_path)
    test_examples = read_issue_examples(test_path)

    pipeline = Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    analyzer=config.analyzer,
                    ngram_range=(config.ngram_min, config.ngram_max),
                    max_features=config.max_features,
                    min_df=config.min_df,
                    sublinear_tf=config.sublinear_tf,
                    lowercase=config.lowercase,
                    strip_accents=config.strip_accents,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=config.logistic_regression_max_iter,
                    C=config.logistic_regression_c,
                    class_weight=config.class_weight,
                    random_state=config.random_state,
                    n_jobs=None,
                ),
            ),
        ]
    )

    fit_started = perf_counter()
    pipeline.fit(
        [example.text for example in train_examples],
        [example.target for example in train_examples],
    )
    fit_seconds = perf_counter() - fit_started

    metrics: dict[str, Any] = {"timing": {"fit_seconds": fit_seconds}}
    reports: dict[str, Any] = {}

    for split_name, examples in ("validation", val_examples), ("test", test_examples):
        split_metrics, split_report, predict_seconds = evaluate_split(
            pipeline=pipeline,
            examples=examples,
            split_name=split_name,
        )
        metrics[split_name] = split_metrics
        metrics["timing"][f"{split_name}_predict_seconds"] = predict_seconds
        reports[split_name] = split_report

    vocabulary = pipeline.named_steps["tfidf"].vocabulary_
    metrics["model_size"] = {
        "vocabulary_size": len(vocabulary),
        "labels": list(LABELS),
    }
    return metrics, reports


def evaluate_split(
    pipeline: Any,
    examples: list[Any],
    split_name: str,
) -> tuple[dict[str, Any], dict[str, Any], float]:
    """Evaluate one split using shared metrics for the comparison table."""
    dependencies = _load_baseline_dependencies()
    accuracy_score = dependencies["accuracy_score"]
    classification_report = dependencies["classification_report"]
    confusion_matrix = dependencies["confusion_matrix"]
    f1_score = dependencies["f1_score"]

    texts = [example.text for example in examples]
    actual = [example.target for example in examples]

    started = perf_counter()
    predicted = list(pipeline.predict(texts))
    predict_seconds = perf_counter() - started

    report = classification_report(
        actual,
        predicted,
        labels=list(LABELS),
        output_dict=True,
        zero_division=0,
    )
    matrix = confusion_matrix(actual, predicted, labels=list(LABELS)).tolist()
    metrics = {
        "split": split_name,
        "examples": len(examples),
        "accuracy": float(accuracy_score(actual, predicted)),
        "macro_f1": float(f1_score(actual, predicted, labels=list(LABELS), average="macro")),
        "weighted_f1": float(f1_score(actual, predicted, labels=list(LABELS), average="weighted")),
        "per_class_f1": {label: float(report[label]["f1-score"]) for label in LABELS},
        "confusion_matrix_labels": list(LABELS),
        "confusion_matrix": matrix,
        "predict_seconds": predict_seconds,
        "examples_per_second": len(examples) / predict_seconds if predict_seconds else None,
    }
    return metrics, report, predict_seconds


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write stable JSON for small run-evidence files."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _load_baseline_dependencies() -> dict[str, Any]:
    """Import sklearn only when the baseline command is invoked."""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
        from sklearn.pipeline import Pipeline
    except ImportError as exc:
        raise RuntimeError(
            "Classical baseline dependencies are missing. Install the model-server train extra first."
        ) from exc

    return {
        "TfidfVectorizer": TfidfVectorizer,
        "LogisticRegression": LogisticRegression,
        "Pipeline": Pipeline,
        "accuracy_score": accuracy_score,
        "classification_report": classification_report,
        "confusion_matrix": confusion_matrix,
        "f1_score": f1_score,
    }


def main() -> None:
    args = parse_args()
    config = ClassicalBaselineConfig(run_name=args.run_name)
    manifest = build_run_manifest(
        config=config,
        train_path=args.train_path,
        val_path=args.val_path,
        test_path=args.test_path,
    )
    write_json(args.run_dir / "run_manifest.json", manifest)
    metrics, reports = train_and_evaluate(
        config=config,
        train_path=args.train_path,
        val_path=args.val_path,
        test_path=args.test_path,
    )
    write_json(args.run_dir / "metrics.json", metrics)
    write_json(args.run_dir / "classification_report.json", reports)


if __name__ == "__main__":
    main()
