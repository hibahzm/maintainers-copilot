"""Embed parent-child RAG chunks and store them in PostgreSQL/pgvector.

This is an experiment/indexing script, not a long-running API service. It uses
our selected embedding model, `intfloat/e5-small-v2`, and writes vectors into the
`rag_chunks.embedding` column created by Alembic.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

DEFAULT_CHUNKS_PATH = Path("data/rag/chunks/parent_child_chunks.jsonl")
DEFAULT_DATABASE_URL = "postgresql://copilot:copilot-dev-only@localhost:5432/copilot"
DEFAULT_EMBEDDING_MODEL = "intfloat/e5-small-v2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks-path", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL))
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--device", default="auto", choices=("auto", "cpu", "cuda"))
    parser.add_argument("--replace", action="store_true", help="Delete existing RAG chunks/sources before indexing.")
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


class E5Embedder:
    def __init__(self, model_name: str, *, device: str, batch_size: int) -> None:
        try:
            import torch
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - depends on indexing runtime
            raise SystemExit(
                "Missing indexing dependencies. Install them in your indexing runtime:\n"
                "  pip install sentence-transformers asyncpg\n"
            ) from exc

        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        elif device == "cuda" and not torch.cuda.is_available():
            print("CUDA was requested, but this Torch build cannot use CUDA. Falling back to CPU.")
            device = "cpu"

        self.model_name = model_name
        self.batch_size = batch_size
        self.device = device
        self.model = SentenceTransformer(model_name, device=device)

    def encode(self, texts: list[str], *, kind: str) -> list[list[float]]:
        prefix = "query: " if kind == "query" else "passage: "
        prefixed = [f"{prefix}{text}" for text in texts]
        vectors = self.model.encode(
            prefixed,
            batch_size=self.batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=True,
        )
        return [[float(value) for value in vector] for vector in vectors]


def vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"


def source_rows(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources: dict[str, dict[str, Any]] = {}
    for chunk in chunks:
        source_id = chunk["source_id"]
        if source_id in sources:
            continue
        sources[source_id] = {
            "id": source_id,
            "source_type": chunk.get("source_type") or "unknown",
            "source_path": chunk.get("source_path"),
            "title": chunk.get("title"),
            "metadata": chunk.get("metadata") or {},
        }
    return list(sources.values())


async def index_chunks(args: argparse.Namespace) -> dict[str, Any]:
    try:
        import asyncpg
    except ImportError as exc:  # pragma: no cover - depends on indexing runtime
        raise SystemExit(
            "Missing database dependency. Install it in your indexing runtime:\n"
            "  pip install asyncpg\n"
        ) from exc

    chunks = load_jsonl(args.chunks_path)
    if not chunks:
        raise RuntimeError(f"No chunks found at {args.chunks_path}.")

    embedder = E5Embedder(args.embedding_model, device=args.device, batch_size=args.batch_size)
    texts = [chunk.get("text", "") for chunk in chunks]
    vectors = embedder.encode(texts, kind="passage")

    connection = await asyncpg.connect(args.database_url)
    try:
        async with connection.transaction():
            if args.replace:
                await connection.execute("DELETE FROM rag_chunks")
                await connection.execute("DELETE FROM rag_sources")

            await connection.executemany(
                """
                INSERT INTO rag_sources (id, source_type, source_path, title, metadata)
                VALUES ($1, $2, $3, $4, $5::jsonb)
                ON CONFLICT (id) DO UPDATE SET
                    source_type = EXCLUDED.source_type,
                    source_path = EXCLUDED.source_path,
                    title = EXCLUDED.title,
                    metadata = EXCLUDED.metadata
                """,
                [
                    (
                        source["id"],
                        source["source_type"],
                        source["source_path"],
                        source["title"],
                        json.dumps(source["metadata"], sort_keys=True),
                    )
                    for source in source_rows(chunks)
                ],
            )

            await connection.executemany(
                """
                INSERT INTO rag_chunks (
                    id, source_id, parent_id, chunk_strategy, title, parent_title, text,
                    metadata, start_char, end_char, start_word, end_word,
                    embedding, embedding_model
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10, $11, $12, $13::vector, $14)
                ON CONFLICT (id) DO UPDATE SET
                    source_id = EXCLUDED.source_id,
                    parent_id = EXCLUDED.parent_id,
                    chunk_strategy = EXCLUDED.chunk_strategy,
                    title = EXCLUDED.title,
                    parent_title = EXCLUDED.parent_title,
                    text = EXCLUDED.text,
                    metadata = EXCLUDED.metadata,
                    start_char = EXCLUDED.start_char,
                    end_char = EXCLUDED.end_char,
                    start_word = EXCLUDED.start_word,
                    end_word = EXCLUDED.end_word,
                    embedding = EXCLUDED.embedding,
                    embedding_model = EXCLUDED.embedding_model
                """,
                [
                    (
                        chunk["chunk_id"],
                        chunk["source_id"],
                        chunk.get("parent_id"),
                        chunk.get("chunk_strategy") or "parent_child_sections",
                        chunk.get("title"),
                        chunk.get("parent_title"),
                        chunk.get("text") or "",
                        json.dumps(chunk.get("metadata") or {}, sort_keys=True),
                        chunk.get("start_char"),
                        chunk.get("end_char"),
                        chunk.get("start_word"),
                        chunk.get("end_word"),
                        vector_literal(vector),
                        args.embedding_model,
                    )
                    for chunk, vector in zip(chunks, vectors, strict=True)
                ],
            )
    finally:
        await connection.close()

    return {
        "chunks_indexed": len(chunks),
        "sources_indexed": len(source_rows(chunks)),
        "embedding_model": args.embedding_model,
        "embedding_device": embedder.device,
        "chunks_path": args.chunks_path.as_posix(),
    }


def main() -> None:
    args = parse_args()
    result = asyncio.run(index_chunks(args))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
