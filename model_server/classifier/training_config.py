"""Reproducible settings for the first issue-classifier fine-tuning run."""

from dataclasses import dataclass

LABEL_TO_ID = {
    "bug": 0,
    "feature": 1,
    "docs": 2,
    "question": 3,
}


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    """A compact first-run recipe that can be serialized into the run manifest."""

    run_name: str
    output_dir: str
    model_name: str = "distilbert-base-uncased"
    max_length: int = 384
    learning_rate: float = 2e-5
    train_batch_size: int = 16
    eval_batch_size: int = 32
    num_train_epochs: int = 3
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1
    logging_steps: int = 25
    seed: int = 42
    freeze_encoder_layers: int = 4
    freeze_policy: str = "freeze lower 4 DistilBERT encoder blocks; train top 2 blocks + head"
    wandb_project: str = "maintainers-copilot-week7"
