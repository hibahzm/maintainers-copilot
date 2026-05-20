"""Evaluate sparse BM25, dense, and tuned hybrid retrieval on RAG golden questions."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.rag.evaluate_retrieval import (
    DEFAULT_GOLDEN_PATH,
    cosine,
    embed,
    load_json,
    load_jsonl,
    metrics,
    ndcg_at_k,
    passes_filter,
    reciprocal_rank,
    tokenize,
)

DEFAULT_CHUNKS_PATH = Path("data/rag/chunks/parent_child_chunks.jsonl")
DEFAULT_OUTPUT_PATH = Path("evals/rag_hybrid_tuning_results.json")
DEFAULT_WEIGHTS = (0.0, 0.25, 0.5, 0.65, 0.75, 0.85, 1.0)


@dataclass(frozen=True)
class HybridConfig:
    name: str
    chunk_strategy: str
    dense_embedding: str
    sparse_embedding: str
    vector_dimensions: int
    top_k: int
    dense_weight: float
    sparse_weight: float
    uses_metadata_filter: bool
    bm25_k1: float = 1.5
    bm25_b: float = 0.75


class BM25Index:
    def __init__(self, chunks: list[dict[str, Any]], *, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.doc_tokens: dict[str, list[str]] = {}
        self.doc_lengths: dict[str, int] = {}
        self.term_frequencies: dict[str, Counter[str]] = {}
        document_frequencies: Counter[str] = Counter()

        for chunk in chunks:
            chunk_id = chunk["chunk_id"]
            tokens = tokenize(chunk.get("text", ""))
            self.doc_tokens[chunk_id] = tokens
            self.doc_lengths[chunk_id] = len(tokens)
            term_frequency = Counter(tokens)
            self.term_frequencies[chunk_id] = term_frequency
            for token in term_frequency:
                document_frequencies[token] += 1

        self.document_count = len(chunks)
        self.average_doc_length = sum(self.doc_lengths.values()) / self.document_count if self.document_count else 0.0
        self.idf = {
            token: math.log(1 + (self.document_count - df + 0.5) / (df + 0.5))
            for token, df in document_frequencies.items()
        }

    def score(self, query: str, chunk_id: str) -> float:
        query_terms = tokenize(query)
        if not query_terms:
            return 0.0
        doc_length = self.doc_lengths.get(chunk_id, 0)
        if not doc_length:
            return 0.0
        term_frequency = self.term_frequencies[chunk_id]
        score = 0.0
        for term in query_terms:
            frequency = term_frequency.get(term, 0)
            if not frequency:
                continue
            idf = self.idf.get(term, 0.0)
            denominator = frequency + self.k1 * (1 - self.b + self.b * doc_length / (self.average_doc_length or 1.0))
            score += idf * (frequency * (self.k1 + 1)) / denominator
        return score


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks-path", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--golden-path", type=Path, default=DEFAULT_GOLDEN_PATH)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--dimensions", type=int, default=512)
    parser.add_argument("--weights", type=float, nargs="*", default=list(DEFAULT_WEIGHTS))
    parser.add_argument("--use-metadata-filter", action="store_true")
    return parser.parse_args()


def minmax(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    low = min(values.values())
    high = max(values.values())
    if math.isclose(low, high):
        return {key: 0.0 for key in values}
    return {key: (value - low) / (high - low) for key, value in values.items()}


def rank_chunks(
    *,
    query: str,
    chunks: list[dict[str, Any]],
    chunk_vectors: dict[str, dict[int, float]],
    bm25: BM25Index,
    dimensions: int,
    top_k: int,
    dense_weight: float,
    metadata_filter: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    query_vector = embed(query, dimensions)
    eligible_chunks = [chunk for chunk in chunks if passes_filter(chunk, metadata_filter)]
    dense_scores = {chunk["chunk_id"]: cosine(query_vector, chunk_vectors[chunk["chunk_id"]]) for chunk in eligible_chunks}
    sparse_scores = {chunk["chunk_id"]: bm25.score(query, chunk["chunk_id"]) for chunk in eligible_chunks}
    normalized_dense = minmax(dense_scores)
    normalized_sparse = minmax(sparse_scores)
    sparse_weight = 1.0 - dense_weight

    scored = []
    for chunk in eligible_chunks:
        chunk_id = chunk["chunk_id"]
        score = dense_weight * normalized_dense.get(chunk_id, 0.0) + sparse_weight * normalized_sparse.get(chunk_id, 0.0)
        scored.append(
            {
                "chunk_id": chunk_id,
                "source_id": chunk["source_id"],
                "title": chunk.get("title"),
                "score": score,
                "dense_score": dense_scores[chunk_id],
                "sparse_score": sparse_scores[chunk_id],
                "source_type": chunk.get("source_type"),
                "metadata": chunk.get("metadata", {}),
            }
        )
    return sorted(scored, key=lambda item: item["score"], reverse=True)[:top_k]


def evaluate_weight(args: argparse.Namespace, *, dense_weight: float, chunks: list[dict[str, Any]], golden: list[dict[str, Any]], chunk_vectors: dict[str, dict[int, float]], bm25: BM25Index) -> dict[str, Any]:
    config = HybridConfig(
        name=f"parent_child_hybrid_dense_{dense_weight:.2f}",
        chunk_strategy="parent_child_sections",
        dense_embedding=f"hash_dense_{args.dimensions}",
        sparse_embedding="bm25",
        vector_dimensions=args.dimensions,
        top_k=args.top_k,
        dense_weight=dense_weight,
        sparse_weight=1.0 - dense_weight,
        uses_metadata_filter=args.use_metadata_filter,
    )
    rows = []
    for record in golden:
        relevant_sources = set(record["ground_truth_source_ids"])
        metadata_filter = record.get("metadata_filter") if args.use_metadata_filter else None
        results = rank_chunks(
            query=record["question"],
            chunks=chunks,
            chunk_vectors=chunk_vectors,
            bm25=bm25,
            dimensions=args.dimensions,
            top_k=args.top_k,
            dense_weight=dense_weight,
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


def choose_best_hybrid(runs: list[dict[str, Any]]) -> dict[str, Any]:
    hybrid_runs = [
        run
        for run in runs
        if 0.0 < run["config"]["dense_weight"] < 1.0
    ]
    if not hybrid_runs:
        raise ValueError("At least one non-zero sparse+dense hybrid weight is required.")
    return choose_best(hybrid_runs)


def main() -> None:
    args = parse_args()
    chunks = load_jsonl(args.chunks_path)
    golden = load_json(args.golden_path)
    chunk_vectors = {chunk["chunk_id"]: embed(chunk.get("text", ""), args.dimensions) for chunk in chunks}
    bm25 = BM25Index(chunks)
    runs = [
        evaluate_weight(
            args,
            dense_weight=weight,
            chunks=chunks,
            golden=golden,
            chunk_vectors=chunk_vectors,
            bm25=bm25,
        )
        for weight in args.weights
    ]
    best = choose_best(runs)
    best_hybrid = choose_best_hybrid(runs)
    output = {
        "created_at": datetime.now(UTC).isoformat(),
        "chunks_path": args.chunks_path.as_posix(),
        "golden_path": args.golden_path.as_posix(),
        "tuning_metric_order": ["mrr_at_10", "recall_at_10", "ndcg_at_10"],
        "runs": [{"config": run["config"], "metrics": run["metrics"]} for run in runs],
        "best_overall": best,
        "best_hybrid": best_hybrid,
    }
    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "best_overall_config": best["config"],
                "best_overall_metrics": best["metrics"],
                "best_hybrid_config": best_hybrid["config"],
                "best_hybrid_metrics": best_hybrid["metrics"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
