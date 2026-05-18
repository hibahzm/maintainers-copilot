"""Fine-tune the first encoder classifier experiment on the Week 7 issue dataset."""

import argparse
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from model_server.classifier.training_config import LABEL_TO_ID, TrainingConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-path", type=Path, default=Path("data/train.jsonl"))
    parser.add_argument("--val-path", type=Path, default=Path("data/val.jsonl"))
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/classifier"))
    parser.add_argument("--run-name", default=None)
    return parser.parse_args()


@dataclass(frozen=True, slots=True)
class DatasetFingerprint:
    """Stable facts that let a future model card recover the exact training inputs."""

    path: str
    sha256: str
    examples: int


def prepare_run(
    train_path: Path,
    val_path: Path,
    output_root: Path,
    run_name: str | None,
) -> tuple[TrainingConfig, Path, dict[str, DatasetFingerprint]]:
    """Build the immutable config and dataset fingerprints for one experiment."""
    resolved_run_name = run_name or _default_run_name()
    run_dir = output_root / resolved_run_name
    config = TrainingConfig(run_name=resolved_run_name, output_dir=str(run_dir))
    fingerprints = {
        "train": fingerprint_jsonl(train_path),
        "val": fingerprint_jsonl(val_path),
    }
    return config, run_dir, fingerprints


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


def build_run_manifest(
    config: TrainingConfig,
    fingerprints: dict[str, DatasetFingerprint],
) -> dict[str, Any]:
    """Capture every fact needed to recover the first training run later."""
    return {
        "created_at": datetime.now(UTC).isoformat(),
        "experiment": "first_encoder_finetune",
        "config": asdict(config),
        "labels": LABEL_TO_ID,
        "dataset": {name: asdict(fingerprint) for name, fingerprint in fingerprints.items()},
        "freeze_policy": config.freeze_policy,
        "logger": {
            "backend": "wandb",
            "project": config.wandb_project,
            "run_name": config.run_name,
        },
    }


def write_run_manifest(run_dir: Path, manifest: dict[str, Any]) -> None:
    """Persist the run manifest before training starts."""
    run_dir.mkdir(parents=True, exist_ok=True)
    with (run_dir / "run_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")


def train(config: TrainingConfig, run_dir: Path, manifest: dict[str, Any]) -> dict[str, float]:
    """Run the first transformer fine-tuning experiment."""
    dependencies = _load_training_dependencies()
    load_dataset = dependencies["load_dataset"]
    np = dependencies["np"]
    accuracy_score = dependencies["accuracy_score"]
    f1_score = dependencies["f1_score"]
    AutoModelForSequenceClassification = dependencies["AutoModelForSequenceClassification"]
    AutoTokenizer = dependencies["AutoTokenizer"]
    DataCollatorWithPadding = dependencies["DataCollatorWithPadding"]
    Trainer = dependencies["Trainer"]
    TrainingArguments = dependencies["TrainingArguments"]

    data_files = {
        "train": manifest["dataset"]["train"]["path"],
        "validation": manifest["dataset"]["val"]["path"],
    }
    dataset = load_dataset("json", data_files=data_files)

    tokenizer = AutoTokenizer.from_pretrained(config.model_name)

    def tokenize(batch: dict[str, list[str]]) -> dict[str, Any]:
        texts = [
            compose_issue_text(title=title, body=body)
            for title, body in zip(batch["title"], batch["body"], strict=True)
        ]
        encoded = tokenizer(texts, truncation=True, max_length=config.max_length)
        encoded["labels"] = [LABEL_TO_ID[target] for target in batch["target"]]
        return encoded

    tokenized = dataset.map(tokenize, batched=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        config.model_name,
        num_labels=len(LABEL_TO_ID),
        id2label={value: key for key, value in LABEL_TO_ID.items()},
        label2id=LABEL_TO_ID,
    )
    freeze_lower_encoder_layers(model=model, layer_count=config.freeze_encoder_layers)

    def compute_metrics(eval_prediction: Any) -> dict[str, float]:
        logits, labels = eval_prediction
        predictions = np.argmax(logits, axis=-1)
        return {
            "accuracy": float(accuracy_score(labels, predictions)),
            "macro_f1": float(f1_score(labels, predictions, average="macro")),
        }

    os.environ.setdefault("WANDB_PROJECT", config.wandb_project)
    training_args = TrainingArguments(
        output_dir=str(run_dir / "checkpoints"),
        learning_rate=config.learning_rate,
        per_device_train_batch_size=config.train_batch_size,
        per_device_eval_batch_size=config.eval_batch_size,
        num_train_epochs=config.num_train_epochs,
        weight_decay=config.weight_decay,
        warmup_ratio=config.warmup_ratio,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_strategy="steps",
        logging_steps=config.logging_steps,
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        greater_is_better=True,
        seed=config.seed,
        report_to=["wandb"],
        run_name=config.run_name,
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["validation"],
        processing_class=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=compute_metrics,
    )
    trainer.train()
    metrics = trainer.evaluate()
    trainer.save_model(str(run_dir / "model"))
    tokenizer.save_pretrained(str(run_dir / "model"))
    return {key: float(value) for key, value in metrics.items() if isinstance(value, int | float)}


def compose_issue_text(title: str, body: str) -> str:
    """Keep preprocessing explicit and easy to defend in DECISIONS.md later."""
    return f"{title.strip()}\n\n{body.strip()}".strip()


def freeze_lower_encoder_layers(model: Any, layer_count: int) -> None:
    """Freeze the lower DistilBERT encoder blocks for the first experiment."""
    encoder_layers = getattr(getattr(model, "distilbert", None), "transformer", None)
    layers = getattr(encoder_layers, "layer", None)
    if layers is None:
        raise ValueError("Freeze policy expects a DistilBERT-style encoder stack.")

    for layer in layers[:layer_count]:
        for parameter in layer.parameters():
            parameter.requires_grad = False


def write_metrics(run_dir: Path, metrics: dict[str, float]) -> None:
    """Persist final validation metrics beside the run manifest."""
    with (run_dir / "metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _load_training_dependencies() -> dict[str, Any]:
    """Import optional training dependencies only when the training command is invoked."""
    try:
        import numpy as np
        from datasets import load_dataset
        from sklearn.metrics import accuracy_score, f1_score
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            DataCollatorWithPadding,
            Trainer,
            TrainingArguments,
        )
    except ImportError as exc:
        raise RuntimeError(
            "Training dependencies are missing. Install the model-server train extra first."
        ) from exc

    return {
        "np": np,
        "load_dataset": load_dataset,
        "accuracy_score": accuracy_score,
        "f1_score": f1_score,
        "AutoModelForSequenceClassification": AutoModelForSequenceClassification,
        "AutoTokenizer": AutoTokenizer,
        "DataCollatorWithPadding": DataCollatorWithPadding,
        "Trainer": Trainer,
        "TrainingArguments": TrainingArguments,
    }


def _default_run_name() -> str:
    return datetime.now(UTC).strftime("distilbert-%Y%m%dT%H%M%SZ")


def main() -> None:
    args = parse_args()
    config, run_dir, fingerprints = prepare_run(
        train_path=args.train_path,
        val_path=args.val_path,
        output_root=args.output_root,
        run_name=args.run_name,
    )
    manifest = build_run_manifest(config=config, fingerprints=fingerprints)
    write_run_manifest(run_dir=run_dir, manifest=manifest)
    metrics = train(config=config, run_dir=run_dir, manifest=manifest)
    write_metrics(run_dir=run_dir, metrics=metrics)


if __name__ == "__main__":
    main()
