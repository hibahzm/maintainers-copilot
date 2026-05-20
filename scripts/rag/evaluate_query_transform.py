"""Evaluate deterministic query transformation on top of tuned hybrid retrieval."""

from __future__ import annotations

import argparse
import json
import re
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
    validate_golden_coverage,
)

DEFAULT_CHUNKS_PATH = Path("data/rag/chunks/parent_child_chunks.jsonl")
DEFAULT_OUTPUT_PATH = Path("evals/rag_query_transform_results.json")
ISSUE_NUMBER_PATTERN = re.compile(r"#?(\d{4,6})")
CODE_SYMBOL_PATTERN = re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*\b")

EXPANSIONS = {
    "services": "compose stack api backend model-server chatbot widget migrate db redis minio vault",
    "secrets": "vault api key llm_api_key redaction secret runtime",
    "runtime secrets": "vault api key llm_api_key redaction secret runtime",
    "model artifact": "sha256 fingerprint artifact model weights drive minio",
    "artifacts": "sha256 fingerprint artifact model weights drive minio",
    "advanced rag": "chunking hybrid retrieval bm25 dense reranking metadata filtering query transformation golden set",
    "jsonl": "dataset rows issue bodies secrets gitignore drive minio",
    "read_csv": "read_csv csv parser io pandas",
    "value_counts": "value_counts name parameter pandas series dataframe",
    "hash_pandas_object": "hash_pandas_object hash pandas object sum",
    "multiindex": "MultiIndex levels index filtering pandas",
    "settingwithcopywarning": "SettingWithCopyWarning documentation docs warning pandas",
}


@dataclass(frozen=True)
class QueryTransformConfig:
    name: str = "deterministic_issue_query_expansion"
    base_retriever: str = "parent_child_hybrid_dense_0.25_sparse_0.75"
    dense_weight: float = 0.25
    sparse_weight: float = 0.75
    top_k: int = 10
    uses_metadata_filter: bool = True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks-path", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--golden-path", type=Path, default=DEFAULT_GOLDEN_PATH)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--dimensions", type=int, default=512)
    parser.add_argument("--dense-weight", type=float, default=0.25)
    parser.add_argument("--use-metadata-filter", dest="use_metadata_filter", action="store_true", default=True)
    parser.add_argument("--no-metadata-filter", dest="use_metadata_filter", action="store_false")
    return parser.parse_args()


def transform_query(query: str) -> str:
    additions: list[str] = []
    lowered = query.lower()

    for phrase, expansion in EXPANSIONS.items():
        if phrase in lowered:
            additions.append(expansion)

    for issue_number in ISSUE_NUMBER_PATTERN.findall(query):
        additions.append(f"pandas-dev/pandas#{issue_number} issue {issue_number}")

    symbols = [symbol for symbol in CODE_SYMBOL_PATTERN.findall(query) if "_" in symbol or "." in symbol]
    if symbols:
        additions.append(" ".join(symbols))

    if not additions:
        return query
    return f"{query}\n\nExpanded maintainer retrieval terms: {' '.join(additions)}"


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    config = QueryTransformConfig(
        dense_weight=args.dense_weight,
        sparse_weight=1.0 - args.dense_weight,
        top_k=args.top_k,
        uses_metadata_filter=args.use_metadata_filter,
    )
    chunks = load_jsonl(args.chunks_path)
    golden = load_json(args.golden_path)
    validate_golden_coverage(chunks, golden)
    chunk_vectors = {chunk["chunk_id"]: embed(chunk.get("text", ""), args.dimensions) for chunk in chunks}
    bm25 = BM25Index(chunks)

    rows = []
    for record in golden:
        relevant_sources = set(record["ground_truth_source_ids"])
        transformed_query = transform_query(record["question"])
        metadata_filter = record.get("metadata_filter") if args.use_metadata_filter else None
        results = rank_chunks(
            query=transformed_query,
            chunks=chunks,
            chunk_vectors=chunk_vectors,
            bm25=bm25,
            dimensions=args.dimensions,
            top_k=args.top_k,
            dense_weight=args.dense_weight,
            metadata_filter=metadata_filter,
        )
        retrieved_source_ids = [result["source_id"] for result in results]
        row = {
            "id": record["id"],
            "question": record["question"],
            "transformed_query": transformed_query,
            "query_changed": transformed_query != record["question"],
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
        "changed_queries": sum(1 for row in rows if row["query_changed"]),
        "rows": rows,
    }


def main() -> None:
    args = parse_args()
    output = evaluate(args)
    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"changed_queries": output["changed_queries"], "metrics": output["metrics"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
