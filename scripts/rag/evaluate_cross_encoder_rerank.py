"""Evaluate cross-encoder reranking over tuned hybrid RAG candidates.

This script intentionally keeps the heavy reranker dependency out of the Docker
services. Run it in Colab or another experiment runtime with torch/transformers
installed, then commit only the small JSON results file.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.rag.evaluate_hybrid_retrieval import BM25Index, rank_chunks
from scripts.rag.evaluate_retrieval import (
    DEFAULT_GOLDEN_PATH,
    embed,
    load_json,
    load_jsonl,
    metrics,
    ndcg_at_k,
    reciprocal_rank,
)

DEFAULT_CHUNKS_PATH = Path("data/rag/chunks/parent_child_chunks.jsonl")
DEFAULT_OUTPUT_PATH = Path("evals/rag_cross_encoder_rerank_results.json")
DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@dataclass(frozen=True)
class CrossEncoderRerankConfig:
    name: str = "parent_child_hybrid_cross_encoder_rerank"
    first_stage_retriever: str = "parent_child_hybrid_dense_0.25_sparse_0.75"
    reranker_model: str = DEFAULT_RERANKER_MODEL
    dense_weight: float = 0.25
    sparse_weight: float = 0.75
    candidate_k: int = 25
    top_k: int = 10
    uses_metadata_filter: bool = True
    max_length: int = 512


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks-path", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--golden-path", type=Path, default=DEFAULT_GOLDEN_PATH)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--reranker-model", default=DEFAULT_RERANKER_MODEL)
    parser.add_argument("--candidate-k", type=int, default=25)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--dimensions", type=int, default=512)
    parser.add_argument("--dense-weight", type=float, default=0.25)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--device", default="auto", choices=("auto", "cpu", "cuda"))
    parser.add_argument("--use-metadata-filter", dest="use_metadata_filter", action="store_true", default=True)
    parser.add_argument("--no-metadata-filter", dest="use_metadata_filter", action="store_false")
    return parser.parse_args()


class CrossEncoderScorer:
    def __init__(self, model_name: str, *, device: str, max_length: int, batch_size: int) -> None:
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as exc:  # pragma: no cover - depends on experiment runtime
            raise SystemExit(
                "Missing reranker dependencies. In Colab run:\n"
                "  pip install -q torch transformers\n"
                "Then re-run this script."
            ) from exc

        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.torch = torch
        self.device = device
        self.max_length = max_length
        self.batch_size = batch_size
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.to(device)
        self.model.eval()

    def score(self, query: str, passages: list[str]) -> list[float]:
        scores: list[float] = []
        for start in range(0, len(passages), self.batch_size):
            batch = passages[start : start + self.batch_size]
            encoded = self.tokenizer(
                [query] * len(batch),
                batch,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt",
            )
            encoded = {key: value.to(self.device) for key, value in encoded.items()}
            with self.torch.no_grad():
                logits = self.model(**encoded).logits
            if logits.ndim == 2 and logits.shape[-1] > 1:
                batch_scores = logits[:, -1]
            else:
                batch_scores = logits.reshape(-1)
            scores.extend(float(value) for value in batch_scores.detach().cpu().tolist())
        return scores


def rerank_candidates(
    *,
    query: str,
    candidates: list[dict[str, Any]],
    chunk_by_id: dict[str, dict[str, Any]],
    scorer: CrossEncoderScorer,
    top_k: int,
) -> list[dict[str, Any]]:
    passages = [chunk_by_id[candidate["chunk_id"]].get("text", "") for candidate in candidates]
    rerank_scores = scorer.score(query, passages)
    reranked = []
    for candidate, rerank_score in zip(candidates, rerank_scores, strict=True):
        updated = dict(candidate)
        updated["hybrid_score"] = updated.pop("score")
        updated["rerank_score"] = rerank_score
        reranked.append(updated)
    return sorted(reranked, key=lambda item: item["rerank_score"], reverse=True)[:top_k]


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    config = CrossEncoderRerankConfig(
        reranker_model=args.reranker_model,
        dense_weight=args.dense_weight,
        sparse_weight=1.0 - args.dense_weight,
        candidate_k=args.candidate_k,
        top_k=args.top_k,
        uses_metadata_filter=args.use_metadata_filter,
        max_length=args.max_length,
    )
    chunks = load_jsonl(args.chunks_path)
    golden = load_json(args.golden_path)
    chunk_by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
    chunk_vectors = {chunk["chunk_id"]: embed(chunk.get("text", ""), args.dimensions) for chunk in chunks}
    bm25 = BM25Index(chunks)
    scorer = CrossEncoderScorer(
        args.reranker_model,
        device=args.device,
        max_length=args.max_length,
        batch_size=args.batch_size,
    )

    rows = []
    for record in golden:
        relevant_sources = set(record["ground_truth_source_ids"])
        metadata_filter = record.get("metadata_filter") if args.use_metadata_filter else None
        first_stage = rank_chunks(
            query=record["question"],
            chunks=chunks,
            chunk_vectors=chunk_vectors,
            bm25=bm25,
            dimensions=args.dimensions,
            top_k=args.candidate_k,
            dense_weight=args.dense_weight,
            metadata_filter=metadata_filter,
        )
        results = rerank_candidates(
            query=record["question"],
            candidates=first_stage,
            chunk_by_id=chunk_by_id,
            scorer=scorer,
            top_k=args.top_k,
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

    return {
        "created_at": datetime.now(UTC).isoformat(),
        "config": asdict(config),
        "chunks_path": args.chunks_path.as_posix(),
        "golden_path": args.golden_path.as_posix(),
        "metrics": metrics(rows),
        "rows": rows,
    }


def main() -> None:
    args = parse_args()
    output = evaluate(args)
    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output["metrics"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
