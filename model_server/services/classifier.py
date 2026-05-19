"""Runtime issue-classification service backed by the selected DistilBERT model."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from model_server.schemas.classifier import ClassifyIssueResponse
from model_server.services.artifacts import fingerprint_directory
from model_server.classifier.text import compose_issue_text
from model_server.classifier.training_config import LABEL_TO_ID

DEFAULT_CLASSIFIER_MODEL_DIR = Path("artifacts/classifier/first-distilbert-freeze4/model")
MAX_LENGTH = 384
LABELS = tuple(LABEL_TO_ID.keys())


class DistilBERTIssueClassifier:
    """Lazy DistilBERT classifier wrapper.

    The model weights are intentionally not committed. Point
    CLASSIFIER_MODEL_DIR at the saved Hugging Face model directory when running
    the model server.
    """

    def __init__(self, model_dir: Path, max_length: int = MAX_LENGTH) -> None:
        self.model_dir = model_dir
        self.max_length = max_length
        self._tokenizer: Any | None = None
        self._model: Any | None = None
        self._torch: Any | None = None
        self._device: Any | None = None
        self._id_to_label: dict[int, str] | None = None
        self._model_artifact_sha256: str | None = None

    @property
    def model_name(self) -> str:
        return "first-distilbert-freeze4"

    def predict(self, *, title: str, body: str) -> ClassifyIssueResponse:
        """Classify one issue and return the highest-probability label."""
        self._ensure_loaded()
        assert self._tokenizer is not None
        assert self._model is not None
        assert self._torch is not None
        assert self._device is not None
        assert self._id_to_label is not None

        text = compose_issue_text(title=title, body=body)
        encoded = self._tokenizer(
            [text],
            truncation=True,
            max_length=self.max_length,
            padding=True,
            return_tensors="pt",
        )
        encoded = {key: value.to(self._device) for key, value in encoded.items()}
        with self._torch.no_grad():
            logits = self._model(**encoded).logits
            probabilities = self._torch.softmax(logits, dim=-1)[0].detach().cpu().tolist()

        scores = {
            self._id_to_label[index]: float(probability)
            for index, probability in enumerate(probabilities)
        }
        label, confidence = max(scores.items(), key=lambda item: item[1])
        return ClassifyIssueResponse(
            label=label,
            confidence=confidence,
            scores=scores,
            model_name=self.model_name,
            model_dir=str(self.model_dir),
            model_artifact_sha256=self._model_artifact_sha256,
        )

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        if not self.model_dir.exists():
            raise FileNotFoundError(
                f"Missing classifier model directory: {self.model_dir}. "
                "Set CLASSIFIER_MODEL_DIR to the saved DistilBERT model path."
            )

        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as exc:  # pragma: no cover - depends on runtime image
            raise RuntimeError("Classifier runtime dependencies are missing.") from exc

        tokenizer = AutoTokenizer.from_pretrained(self.model_dir)
        model = AutoModelForSequenceClassification.from_pretrained(self.model_dir)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        model.eval()

        id_to_label = {int(key): value for key, value in model.config.id2label.items()}
        if set(id_to_label.values()) != set(LABELS):
            raise ValueError(f"Saved classifier labels do not match expected labels: {id_to_label}")

        self._tokenizer = tokenizer
        self._model = model
        self._torch = torch
        self._device = device
        self._id_to_label = id_to_label
        self._model_artifact_sha256 = fingerprint_directory(self.model_dir).sha256


def classifier_model_dir() -> Path:
    return Path(os.getenv("CLASSIFIER_MODEL_DIR", str(DEFAULT_CLASSIFIER_MODEL_DIR)))


@lru_cache(maxsize=1)
def get_classifier() -> DistilBERTIssueClassifier:
    return DistilBERTIssueClassifier(model_dir=classifier_model_dir())
