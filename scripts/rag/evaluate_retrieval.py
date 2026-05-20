"""Evaluate a naive dense-only RAG retrieval baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

LABELS_FOR_FILTER = {"bug", "feature", "docs", "question"}
TOKEN_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_\.]*|\d+(?:\.\d+)*")
DEFAULT_CHUNKS_PATH = Path("data/rag/chunks/naive_fixed_chunks.jsonl")
DEFAULT_GOLDEN_PATH = Path("evals/golden_rag.json")
DEFAULT_OUTPUT_PATH = Path("evals/rag_naive_dense_baseline_results.json")


@dataclass(frozen=True)
class RetrievalConfig:
    name: str = "naive_fixed_hash_dense"
    chunk_strategy: str = "naive_fixed_words"
    embedding: str = "hash_dense_512"
    vector_dimensions: int = 512
    top_k: int = 10
    uses_metadata_filter: bool = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks-path", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--golden-path", type=Path, default=DEFAULT_GOLDEN_PATH)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--dimensions", type=int, default=512)
    parser.add_argument("--use-metadata-filter", action="store_true")
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def tokenize(text: str) -> list[str]:
    return [token.group(0).lower() for token in TOKEN_PATTERN.finditer(text)]


def embed(text: str, dimensions: int) -> dict[int, float]:
    counts: Counter[int] = Counter()
    for token in tokenize(text):
        bucket = int(hashlib.sha256(token.encode("utf-8")).hexdigest()[:8], 16) % dimensions
        counts[bucket] += 1.0
    norm = math.sqrt(sum(value * value for value in counts.values())) or 1.0
    return {index: value / norm for index, value in counts.items()}


def cosine(left: dict[int, float], right: dict[int, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(index, 0.0) for index, value in left.items())


def validate_golden_coverage(chunks: list[dict[str, Any]], golden: list[dict[str, Any]]) -> None:
    available_source_ids = {chunk.get("source_id") for chunk in chunks}
    missing = sorted(
        {
            source_id
            for record in golden
            for source_id in record.get("ground_truth_source_ids", [])
            if source_id not in available_source_ids
        }
    )
    if missing:
        preview = ", ".join(missing[:8])
        suffix = "" if len(missing) <= 8 else f" ... plus {len(missing) - 8} more"
        raise RuntimeError(
            "RAG golden-set sources are missing from the chunk corpus: "
            f"{preview}{suffix}. Rebuild the corpus/chunks before evaluating."
        )


def passes_filter(chunk: dict[str, Any], metadata_filter: dict[str, Any] | None) -> bool:
    if not metadata_filter:
        return True
    metadata = chunk.get("metadata") or {}
    for key, expected in metadata_filter.items():
        if key == "source_type":
            actual = chunk.get("source_type")
        else:
            actual = metadata.get(key)
        if actual != expected:
            return False
    return True


def rank_chunks(
    *,
    query: str,
    chunks: list[dict[str, Any]],
    chunk_vectors: dict[str, dict[int, float]],
    dimensions: int,
    top_k: int,
    metadata_filter: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    query_vector = embed(query, dimensions)
    scored = []
    for chunk in chunks:
        if not passes_filter(chunk, metadata_filter):
            continue
        score = cosine(query_vector, chunk_vectors[chunk["chunk_id"]])
        scored.append(
            {
                "chunk_id": chunk["chunk_id"],
                "source_id": chunk["source_id"],
                "title": chunk.get("title"),
                "score": score,
                "source_type": chunk.get("source_type"),
                "metadata": chunk.get("metadata", {}),
            }
        )
    return sorted(scored, key=lambda item: item["score"], reverse=True)[:top_k]


def reciprocal_rank(results: list[dict[str, Any]], relevant_sources: set[str]) -> float:
    for index, result in enumerate(results, start=1):
        if result["source_id"] in relevant_sources:
            return 1.0 / index
    return 0.0


def dcg_at_k(results: list[dict[str, Any]], relevant_sources: set[str], k: int) -> float:
    score = 0.0
    credited_sources: set[str] = set()
    for index, result in enumerate(results[:k], start=1):
        source_id = result["source_id"]
        relevance = 1.0 if source_id in relevant_sources and source_id not in credited_sources else 0.0
        if relevance:
            credited_sources.add(source_id)
        score += relevance / math.log2(index + 1)
    return score


def ndcg_at_k(results: list[dict[str, Any]], relevant_sources: set[str], k: int) -> float:
    ideal_relevant = min(len(relevant_sources), k)
    if ideal_relevant == 0:
        return 0.0
    ideal_dcg = sum(1.0 / math.log2(index + 1) for index in range(1, ideal_relevant + 1))
    return dcg_at_k(results, relevant_sources, k) / ideal_dcg


def metrics(rows: list[dict[str, Any]], k_values: tuple[int, ...] = (1, 3, 5, 10)) -> dict[str, Any]:
    output: dict[str, Any] = {"examples": len(rows)}
    for k in k_values:
        output[f"recall_at_{k}"] = sum(row[f"hit_at_{k}"] for row in rows) / len(rows)
    output["mrr_at_10"] = sum(row["reciprocal_rank"] for row in rows) / len(rows)
    output["ndcg_at_10"] = sum(row["ndcg_at_10"] for row in rows) / len(rows)
    return output


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    config = RetrievalConfig(top_k=args.top_k, vector_dimensions=args.dimensions, uses_metadata_filter=args.use_metadata_filter)
    chunks = load_jsonl(args.chunks_path)
    golden = load_json(args.golden_path)
    validate_golden_coverage(chunks, golden)
    chunk_vectors = {chunk["chunk_id"]: embed(chunk.get("text", ""), args.dimensions) for chunk in chunks}

    rows = []
    for record in golden:
        relevant_sources = set(record["ground_truth_source_ids"])
        metadata_filter = record.get("metadata_filter") if args.use_metadata_filter else None
        results = rank_chunks(
            query=record["question"],
            chunks=chunks,
            chunk_vectors=chunk_vectors,
            dimensions=args.dimensions,
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
