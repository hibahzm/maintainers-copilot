"""Create naive fixed-size chunks for the local RAG dev corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_CORPUS_PATH = Path("data/rag/raw/dev_corpus.jsonl")
DEFAULT_CHUNKS_PATH = Path("data/rag/chunks/naive_fixed_chunks.jsonl")
DEFAULT_MANIFEST_PATH = Path("data/rag/chunks/naive_fixed_chunks_manifest.json")
TOKEN_PATTERN = re.compile(r"\S+")


@dataclass(frozen=True)
class ChunkManifest:
    strategy: str
    created_at: str
    source_path: str
    output_path: str
    source_documents: int
    chunks: int
    chunk_size_words: int
    overlap_words: int
    sha256: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-path", type=Path, default=DEFAULT_CORPUS_PATH)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--chunk-size-words", type=int, default=180)
    parser.add_argument("--overlap-words", type=int, default=40)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def chunk_record(record: dict[str, Any], *, chunk_size_words: int, overlap_words: int) -> list[dict[str, Any]]:
    text = str(record.get("text") or "")
    tokens = list(TOKEN_PATTERN.finditer(text))
    if not tokens:
        return []
    step = max(1, chunk_size_words - overlap_words)
    chunks: list[dict[str, Any]] = []
    for chunk_index, start_token in enumerate(range(0, len(tokens), step)):
        token_slice = tokens[start_token : start_token + chunk_size_words]
        if not token_slice:
            continue
        start_char = token_slice[0].start()
        end_char = token_slice[-1].end()
        chunk_text = text[start_char:end_char].strip()
        if not chunk_text:
            continue
        chunks.append(
            {
                "chunk_id": f"{record['id']}::fixed-{chunk_size_words}-{overlap_words}::{chunk_index:04d}",
                "source_id": record["id"],
                "source_type": record.get("source_type"),
                "source_path": record.get("source_path"),
                "title": record.get("title"),
                "text": chunk_text,
                "metadata": record.get("metadata", {}),
                "chunk_strategy": "naive_fixed_words",
                "chunk_index": chunk_index,
                "start_char": start_char,
                "end_char": end_char,
                "start_word": start_token,
                "end_word": start_token + len(token_slice),
            }
        )
        if start_token + chunk_size_words >= len(tokens):
            break
    return chunks


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    records = load_jsonl(args.corpus_path)
    chunks = [
        chunk
        for record in records
        for chunk in chunk_record(
            record,
            chunk_size_words=args.chunk_size_words,
            overlap_words=args.overlap_words,
        )
    ]
    write_jsonl(args.output_path, chunks)
    manifest = ChunkManifest(
        strategy="naive_fixed_words",
        created_at=datetime.now(UTC).isoformat(),
        source_path=args.corpus_path.as_posix(),
        output_path=args.output_path.as_posix(),
        source_documents=len(records),
        chunks=len(chunks),
        chunk_size_words=args.chunk_size_words,
        overlap_words=args.overlap_words,
        sha256=sha256_file(args.output_path),
    )
    args.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_path.write_text(json.dumps(asdict(manifest), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"chunks": len(chunks), "sha256": manifest.sha256}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
