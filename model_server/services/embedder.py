"""Local embedding service for RAG query and passage vectors."""

import os
from functools import lru_cache
from typing import Literal, Any

from model_server.schemas.embedder import EmbedTextResponse

DEFAULT_EMBEDDING_MODEL = "intfloat/e5-small-v2"
DEFAULT_MAX_LENGTH = 512


class E5TextEmbedder:
    """Lazy E5 embedder using transformers directly.

    E5 models expect `query:` prefixes for user questions and `passage:` prefixes
    for indexed chunks. We keep this in model-server so backend/chatbot code can
    request embeddings without carrying transformer runtime dependencies.
    """

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL, max_length: int = DEFAULT_MAX_LENGTH) -> None:
        self.model_name = model_name
        self.max_length = max_length
        self._tokenizer: Any | None = None
        self._model: Any | None = None
        self._torch: Any | None = None
        self._device: Any | None = None
        self._dimensions: int | None = None

    def embed(self, texts: list[str], *, input_type: Literal["query", "passage"]) -> EmbedTextResponse:
        self._ensure_loaded()
        assert self._tokenizer is not None
        assert self._model is not None
        assert self._torch is not None
        assert self._device is not None

        prefix = "query: " if input_type == "query" else "passage: "
        encoded = self._tokenizer(
            [prefix + text for text in texts],
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        encoded = {key: value.to(self._device) for key, value in encoded.items()}
        with self._torch.no_grad():
            model_output = self._model(**encoded)
            pooled = self._mean_pool(
                token_embeddings=model_output.last_hidden_state,
                attention_mask=encoded["attention_mask"],
            )
            normalized = self._torch.nn.functional.normalize(pooled, p=2, dim=1)

        embeddings = [[float(value) for value in row] for row in normalized.detach().cpu().tolist()]
        dimensions = len(embeddings[0]) if embeddings else int(self._dimensions or 0)
        return EmbedTextResponse(
            embeddings=embeddings,
            model_name=self.model_name,
            dimensions=dimensions,
            input_type=input_type,
        )

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError as exc:  # pragma: no cover - depends on runtime image
            raise RuntimeError("Embedding runtime dependencies are missing.") from exc

        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        model = AutoModel.from_pretrained(self.model_name)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        model.eval()

        self._tokenizer = tokenizer
        self._model = model
        self._torch = torch
        self._device = device
        self._dimensions = int(model.config.hidden_size)

    def _mean_pool(self, *, token_embeddings: Any, attention_mask: Any) -> Any:
        assert self._torch is not None
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return self._torch.sum(token_embeddings * input_mask_expanded, dim=1) / self._torch.clamp(
            input_mask_expanded.sum(dim=1),
            min=1e-9,
        )


def embedding_model_name() -> str:
    return os.getenv("RAG_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)


@lru_cache(maxsize=1)
def get_embedder() -> E5TextEmbedder:
    return E5TextEmbedder(model_name=embedding_model_name())
