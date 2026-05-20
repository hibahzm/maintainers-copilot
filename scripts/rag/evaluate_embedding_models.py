"""Compare dense embedding models on the RAG golden set.

Run this in Colab or another experiment runtime. It intentionally keeps
sentence-transformers out of the Docker services until the embedding choice is
measured and accepted.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.rag.evaluate_retrieval import (
    DEFAULT_GOLDEN_PATH,
    load_json,
    load_jsonl,
    metrics,
    ndcg_at_k,
    passes_filter,
    reciprocal_rank,
)

DEFAULT_CHUNKS_PATH = Path("data/rag/chunks/parent_child_chunks.jsonl")
DEFAULT_OUTPUT_PATH = Path("evals/rag_embedding_model_comparison_results.json")
DEFAULT_MODELS = (
    "sentence-transformers/all-MiniLM-L6-v2",
    "intfloat/e5-small-v2",
)


@dataclass(frozen=True)
class EmbeddingModelConfig:
    name: str
    model_name: str
    chunk_strategy: str
    retrieval_mode: str
    top_k: int
    uses_metadata_filter: bool
    batch_size: int
    device: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks-path", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--golden-path", type=Path, default=DEFAULT_GOLDEN_PATH)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--embedding-models", nargs="+", default=list(DEFAULT_MODELS))
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--device", default="auto", choices=("auto", "cpu", "cuda"))
    parser.add_argument("--use-metadata-filter", dest="use_metadata_filter", action="store_true", default=True)
    parser.add_argument("--no-metadata-filter", dest="use_metadata_filter", action="store_false")
    return parser.parse_args()


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str, *, device: str, batch_size: int) -> None:
        try:
            import torch
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - depends on experiment runtime
            raise SystemExit(
                "Missing embedding dependencies. In Colab run:\n"
                "  pip install -q sentence-transformers\n"
                "Then re-run this script."
            ) from exc

        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        elif device == "cuda" and not torch.cuda.is_available():
            print("CUDA was requested, but this Torch build cannot use CUDA. Falling back to CPU.")
            device = "cpu"
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.model = SentenceTransformer(model_name, device=device)

    def _prefix(self, texts: list[str], *, kind: str) -> list[str]:
        # E5-family models are trained with explicit query/passsage prefixes.
        if "e5" in self.model_name.lower():
            prefix = "query: " if kind == "query" else "passage: "
            return [prefix + text for text in texts]
        return texts

    def encode(self, texts: list[str], *, kind: str) -> Any:
        return self.model.encode(
            self._prefix(texts, kind=kind),
            batch_size=self.batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=True,
        )


def rank_dense(
    *,
    query: str,
    chunks: list[dict[str, Any]],
    chunk_embeddings: Any,
    embedder: SentenceTransformerEmbedder,
    top_k: int,
    metadata_filter: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    query_embedding = embedder.encode([query], kind="query")[0]
    scores = chunk_embeddings @ query_embedding
    scored = []
    for index, chunk in enumerate(chunks):
        if not passes_filter(chunk, metadata_filter):
            continue
        scored.append(
            {
                "chunk_id": chunk["chunk_id"],
                "source_id": chunk["source_id"],
                "title": chunk.get("title"),
                "score": float(scores[index]),
                "source_type": chunk.get("source_type"),
                "metadata": chunk.get("metadata", {}),
            }
        )
    return sorted(scored, key=lambda item: item["score"], reverse=True)[:top_k]


def evaluate_model(
    *,
    model_name: str,
    chunks: list[dict[str, Any]],
    golden: list[dict[str, Any]],
    args: argparse.Namespace,
) -> dict[str, Any]:
    embedder = SentenceTransformerEmbedder(model_name, device=args.device, batch_size=args.batch_size)
    config = EmbeddingModelConfig(
        name=f"dense_embedding_{model_name.split('/')[-1]}",
        model_name=model_name,
        chunk_strategy="parent_child_sections",
        retrieval_mode="dense_only_cosine",
        top_k=args.top_k,
        uses_metadata_filter=args.use_metadata_filter,
        batch_size=args.batch_size,
        device=embedder.device,
    )
    chunk_texts = [chunk.get("text", "") for chunk in chunks]
    chunk_embeddings = embedder.encode(chunk_texts, kind="passage")

    rows = []
    for record in golden:
        relevant_sources = set(record["ground_truth_source_ids"])
        metadata_filter = record.get("metadata_filter") if args.use_metadata_filter else None
        results = rank_dense(
            query=record["question"],
            chunks=chunks,
            chunk_embeddings=chunk_embeddings,
            embedder=embedder,
            top_k=args.top_k,
            metadata_filter=metadata_filter,
        )
        retrieved_source_ids = [result["source_id"] for result in results]
        row = {
            "id": record["id"],
            "question": record["question"],
            "ground_truth_source_ids": sorted(relevant_sources),
            "retrieved_source_ids": retrieved_source_ids,
            "top_chunks": results,
            "reciprocal_rank": reciprocal_rank(results, relevant_sources),
            "ndcg_at_10": ndcg_at_k(results, relevant_sources, 10),
        }
        for k in (1, 3, 5, 10):
            row[f"hit_at_{k}"] = any(source_id in relevant_sources for source_id in retrieved_source_ids[:k])
        rows.append(row)

    return {"config": asdict(config), "metrics": metrics(rows), "rows": rows}


def choose_best(runs: list[dict[str, Any]]) -> dict[str, Any]:
    return max(
        runs,
        key=lambda run: (
            run["metrics"]["mrr_at_10"],
            run["metrics"]["recall_at_10"],
            run["metrics"]["ndcg_at_10"],
        ),
    )


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    chunks = load_jsonl(args.chunks_path)
    golden = load_json(args.golden_path)
    runs = [evaluate_model(model_name=model, chunks=chunks, golden=golden, args=args) for model in args.embedding_models]
    best = choose_best(runs)
    return {
        "created_at": datetime.now(UTC).isoformat(),
        "chunks_path": args.chunks_path.as_posix(),
        "golden_path": args.golden_path.as_posix(),
        "tuning_metric_order": ["mrr_at_10", "recall_at_10", "ndcg_at_10"],
        "runs": [{"config": run["config"], "metrics": run["metrics"]} for run in runs],
        "best": {"config": best["config"], "metrics": best["metrics"]},
        "rows_by_model": {run["config"]["model_name"]: run["rows"] for run in runs},
    }


def main() -> None:
    args = parse_args()
    output = evaluate(args)
    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"best": output["best"], "runs": output["runs"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
