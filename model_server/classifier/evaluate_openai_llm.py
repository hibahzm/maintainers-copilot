"""Evaluate the OpenAI LLM issue-classification baseline on a normalized split."""

import argparse
import json
import os
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter, sleep
from typing import Any

from model_server.classifier.io import fingerprint_jsonl, read_issue_examples
from model_server.classifier.training_config import LABEL_TO_ID

DEFAULT_RUN_NAME = "openai-gpt-4o-mini-test-200"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEST_PATH = Path("data/test_200_balanced.jsonl")
LABELS = tuple(LABEL_TO_ID.keys())
OPENAI_DOCS = {
    "responses_api": "https://developers.openai.com/api/docs/guides/text",
    "structured_outputs": "https://developers.openai.com/api/docs/guides/structured-outputs",
    "models": "https://developers.openai.com/api/docs/models",
}

# Snapshot from OpenAI docs checked on 2026-05-19. Override via CLI if needed.
DEFAULT_INPUT_PRICE_PER_MTOK = 0.15
DEFAULT_OUTPUT_PRICE_PER_MTOK = 0.60


@dataclass(frozen=True, slots=True)
class OpenAILLMBaselineConfig:
    """A reproducible prompt-only OpenAI baseline recipe."""

    run_name: str = DEFAULT_RUN_NAME
    provider: str = "openai"
    model: str = DEFAULT_MODEL
    max_body_chars: int = 2_000
    batch_size: int = 20
    request_sleep_seconds: float = 0.0
    max_retries: int = 3
    input_price_per_mtok: float = DEFAULT_INPUT_PRICE_PER_MTOK
    output_price_per_mtok: float = DEFAULT_OUTPUT_PRICE_PER_MTOK


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-path", type=Path, default=DEFAULT_TEST_PATH)
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=Path("model_server/classifier/runs") / DEFAULT_RUN_NAME,
    )
    parser.add_argument("--run-name", default=DEFAULT_RUN_NAME)
    parser.add_argument("--model", default=os.getenv("OPENAI_LLM_BASELINE_MODEL", DEFAULT_MODEL))
    parser.add_argument("--limit", type=int, default=None, help="Optional pilot limit before the full test run.")
    parser.add_argument("--resume", action="store_true", help="Reuse existing predictions.jsonl and continue missing rows.")
    parser.add_argument("--max-body-chars", type=int, default=2_000)
    parser.add_argument("--batch-size", type=int, default=20, help="Issues per OpenAI request.")
    parser.add_argument("--request-sleep-seconds", type=float, default=0.0)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--input-price-per-mtok", type=float, default=DEFAULT_INPUT_PRICE_PER_MTOK)
    parser.add_argument("--output-price-per-mtok", type=float, default=DEFAULT_OUTPUT_PRICE_PER_MTOK)
    return parser.parse_args()


def build_run_manifest(
    config: OpenAILLMBaselineConfig,
    test_path: Path,
    limit: int | None,
) -> dict[str, Any]:
    """Capture exact inputs, prompt policy, and model choice before inference."""
    return {
        "created_at": datetime.now(UTC).isoformat(),
        "experiment": "openai_llm_baseline",
        "config": asdict(config),
        "labels": LABEL_TO_ID,
        "dataset": {"evaluation": asdict(fingerprint_jsonl(test_path))},
        "limit": limit,
        "evaluation_split": split_name(test_path),
        "prompt": {
            "system": system_prompt(),
            "schema": batch_classification_schema(),
            "text_policy": "batched issue IDs plus title and truncated body; no repository labels are shown to the model",
        },
        "docs": OPENAI_DOCS,
        "artifact_policy": "commit small metrics/manifests/classification reports; do not commit API keys",
    }


def evaluate_openai_baseline(
    config: OpenAILLMBaselineConfig,
    test_path: Path,
    run_dir: Path,
    limit: int | None,
    resume: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run OpenAI predictions and compute classification metrics."""
    dependencies = _load_dependencies()
    classification_report = dependencies["classification_report"]
    confusion_matrix = dependencies["confusion_matrix"]
    f1_score = dependencies["f1_score"]
    accuracy_score = dependencies["accuracy_score"]

    examples = read_issue_examples(test_path)
    if limit is not None:
        examples = examples[:limit]

    prediction_path = run_dir / "predictions.jsonl"
    predictions_by_index = load_existing_predictions(prediction_path) if resume else {}

    client = dependencies["OpenAI"]()
    run_dir.mkdir(parents=True, exist_ok=True)

    for batch_start in range(0, len(examples), config.batch_size):
        batch = [
            (index, examples[index])
            for index in range(batch_start, min(batch_start + config.batch_size, len(examples)))
            if index not in predictions_by_index
        ]
        if not batch:
            continue
        started = perf_counter()
        payload = predict_batch(client=client, config=config, indexed_examples=batch)
        latency_seconds = perf_counter() - started
        predictions = payload["predictions"]
        by_id = {int(item["id"]): item for item in predictions}
        expected_ids = {index for index, _ in batch}
        if set(by_id) != expected_ids:
            raise ValueError(f"Batch response IDs did not match request IDs: expected {expected_ids}, got {set(by_id)}")

        for offset, (index, example) in enumerate(batch):
            item = by_id[index]
            record = {
                "index": index,
                "id": example.identifier,
                "target": example.target,
                "prediction": item["label"],
                "confidence": item.get("confidence"),
                "rationale": item.get("rationale"),
                "latency_seconds": latency_seconds / len(batch),
                "batch_size": len(batch),
                "usage": payload.get("usage", {}) if offset == 0 else {},
                "usage_attribution": "first_record_in_batch" if offset == 0 else "counted_on_first_record_in_batch",
                "response_id": payload.get("response_id"),
            }
            append_jsonl(prediction_path, record)
            predictions_by_index[index] = record
        if config.request_sleep_seconds > 0:
            sleep(config.request_sleep_seconds)

    ordered_predictions = [predictions_by_index[index] for index in range(len(examples))]
    actual = [example.target for example in examples]
    predicted = [record["prediction"] for record in ordered_predictions]

    report = classification_report(
        actual,
        predicted,
        labels=list(LABELS),
        output_dict=True,
        zero_division=0,
    )
    usage = aggregate_usage(ordered_predictions)
    total_latency = sum(float(record.get("latency_seconds", 0.0)) for record in ordered_predictions)
    metrics = {
        "created_at": datetime.now(UTC).isoformat(),
        "split": split_name(test_path),
        "examples": len(examples),
        "accuracy": float(accuracy_score(actual, predicted)),
        "macro_f1": float(f1_score(actual, predicted, labels=list(LABELS), average="macro")),
        "weighted_f1": float(f1_score(actual, predicted, labels=list(LABELS), average="weighted")),
        "per_class_f1": {label: float(report[label]["f1-score"]) for label in LABELS},
        "confusion_matrix_labels": list(LABELS),
        "confusion_matrix": confusion_matrix(actual, predicted, labels=list(LABELS)).tolist(),
        "latency": {
            "total_seconds": total_latency,
            "mean_seconds_per_example": total_latency / len(examples) if examples else None,
            "examples_per_second": len(examples) / total_latency if total_latency else None,
        },
        "usage": usage,
        "estimated_cost_usd": estimate_cost_usd(
            usage=usage,
            input_price_per_mtok=config.input_price_per_mtok,
            output_price_per_mtok=config.output_price_per_mtok,
        ),
    }
    return metrics, {split_name(test_path): report}


def split_name(path: Path) -> str:
    """Use a clear metric split name for full test vs comparison slices."""
    return "test" if path.name == "test.jsonl" else path.stem


def predict_batch(
    client: Any,
    config: OpenAILLMBaselineConfig,
    indexed_examples: list[tuple[int, Any]],
) -> dict[str, Any]:
    """Ask OpenAI to classify a batch of issues, returning parsed structured output."""
    request: dict[str, Any] = {
        "model": config.model,
        "instructions": system_prompt(),
        "input": build_batch_user_prompt(
            indexed_examples=indexed_examples,
            max_body_chars=config.max_body_chars,
        ),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "issue_classification_batch",
                "strict": True,
                "schema": batch_classification_schema(),
            }
        },
    }
    last_exc: Exception | None = None
    for attempt in range(config.max_retries):
        try:
            response = client.responses.create(**request)
            parsed = json.loads(response.output_text)
            predictions = parsed.get("predictions", [])
            for item in predictions:
                label = item.get("label")
                if label not in LABEL_TO_ID:
                    raise ValueError(f"Model returned unsupported label: {label!r}")
            return {
                "predictions": predictions,
                "usage": usage_to_dict(getattr(response, "usage", None)),
                "response_id": getattr(response, "id", None),
            }
        except Exception as exc:  # noqa: BLE001 - retry wrapper for API/parse failures
            last_exc = exc
            if attempt + 1 >= config.max_retries:
                break
            sleep(2**attempt)
    raise RuntimeError("OpenAI LLM baseline request failed after retries.") from last_exc


def system_prompt() -> str:
    prompt_path = Path("prompts/classifier_system.txt")
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8").strip()
    return (
        "You classify GitHub issues for a software maintainer. "
        "Choose exactly one label from: bug, feature, docs, question. "
        "Use only the issue title and body. Return only the structured JSON object requested."
    )


def build_batch_user_prompt(
    indexed_examples: list[tuple[int, Any]],
    max_body_chars: int,
) -> str:
    items: list[str] = []
    for index, example in indexed_examples:
        text = example.text
        if "\n\n" in text:
            title, body = text.split("\n\n", maxsplit=1)
        else:
            title, body = text, ""
        items.append(
            "\n".join(
                [
                    f"ID: {index}",
                    f"Title: {title.strip()}",
                    f"Body: {body.strip()[:max_body_chars]}",
                ]
            )
        )
    return (
        "Classify each GitHub issue below. Return exactly one prediction per ID. "
        "Do not use hidden labels; only infer from title/body.\n\n"
        + "\n\n---\n\n".join(items)
    )


def batch_classification_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "predictions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "description": "The input issue ID."},
                        "label": {
                            "type": "string",
                            "enum": list(LABELS),
                            "description": "The single best issue class.",
                        },
                        "confidence": {
                            "type": "number",
                            "description": "A calibrated confidence estimate from 0 to 1.",
                        },
                        "rationale": {
                            "type": "string",
                            "description": "One short phrase explaining the classification.",
                        },
                    },
                    "required": ["id", "label", "confidence", "rationale"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["predictions"],
        "additionalProperties": False,
    }


def load_existing_predictions(path: Path) -> dict[int, dict[str, Any]]:
    if not path.exists():
        return {}
    predictions: dict[int, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            predictions[int(record["index"])] = record
    return predictions


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
        handle.write("\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def aggregate_usage(predictions: list[dict[str, Any]]) -> dict[str, int]:
    totals: Counter[str] = Counter()
    for record in predictions:
        usage = record.get("usage") or {}
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            value = usage.get(key)
            if isinstance(value, int):
                totals[key] += value
    return dict(totals)


def usage_to_dict(usage: Any) -> dict[str, int]:
    if usage is None:
        return {}
    result: dict[str, int] = {}
    for source, target in (
        ("input_tokens", "input_tokens"),
        ("output_tokens", "output_tokens"),
        ("total_tokens", "total_tokens"),
    ):
        value = getattr(usage, source, None)
        if isinstance(value, int):
            result[target] = value
    return result


def estimate_cost_usd(
    usage: dict[str, int],
    input_price_per_mtok: float,
    output_price_per_mtok: float,
) -> float | None:
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    if input_tokens is None or output_tokens is None:
        return None
    return (input_tokens / 1_000_000 * input_price_per_mtok) + (
        output_tokens / 1_000_000 * output_price_per_mtok
    )


def _load_dependencies() -> dict[str, Any]:
    try:
        from openai import OpenAI
        from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
    except ImportError as exc:
        raise RuntimeError(
            "OpenAI LLM baseline dependencies are missing. Install model-server train dependencies first."
        ) from exc
    return {
        "OpenAI": OpenAI,
        "accuracy_score": accuracy_score,
        "classification_report": classification_report,
        "confusion_matrix": confusion_matrix,
        "f1_score": f1_score,
    }


def main() -> None:
    args = parse_args()
    config = OpenAILLMBaselineConfig(
        run_name=args.run_name,
        model=args.model,
        max_body_chars=args.max_body_chars,
        batch_size=args.batch_size,
        request_sleep_seconds=args.request_sleep_seconds,
        max_retries=args.max_retries,
        input_price_per_mtok=args.input_price_per_mtok,
        output_price_per_mtok=args.output_price_per_mtok,
    )
    manifest = build_run_manifest(config=config, test_path=args.test_path, limit=args.limit)
    write_json(args.run_dir / "run_manifest.json", manifest)
    metrics, report = evaluate_openai_baseline(
        config=config,
        test_path=args.test_path,
        run_dir=args.run_dir,
        limit=args.limit,
        resume=args.resume,
    )
    write_json(args.run_dir / "metrics.json", metrics)
    write_json(args.run_dir / "classification_report.json", report)
    print(json.dumps(metrics, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
