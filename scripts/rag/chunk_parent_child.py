"""Create non-naive parent-child chunks for the local RAG dev corpus."""

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
DEFAULT_CHUNKS_PATH = Path("data/rag/chunks/parent_child_chunks.jsonl")
DEFAULT_MANIFEST_PATH = Path("data/rag/chunks/parent_child_chunks_manifest.json")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
ISSUE_SECTION_PATTERN = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)
TOKEN_PATTERN = re.compile(r"\S+")


@dataclass(frozen=True)
class ChunkManifest:
    strategy: str
    created_at: str
    source_path: str
    output_path: str
    source_documents: int
    parents: int
    chunks: int
    child_size_words: int
    child_overlap_words: int
    sha256: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-path", type=Path, default=DEFAULT_CORPUS_PATH)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--child-size-words", type=int, default=96)
    parser.add_argument("--child-overlap-words", type=int, default=24)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def split_parents(record: dict[str, Any]) -> list[dict[str, Any]]:
    text = str(record.get("text") or "")
    pattern = ISSUE_SECTION_PATTERN if record.get("source_type") == "github_issue" else HEADING_PATTERN
    matches = list(pattern.finditer(text))
    parents: list[dict[str, Any]] = []

    if not matches:
        return [parent_record(record, title=str(record.get("title") or "document"), text=text, index=0, start_char=0, end_char=len(text))]

    # Include intro before first heading if meaningful.
    if matches[0].start() > 0:
        intro = text[: matches[0].start()].strip()
        if intro:
            parents.append(parent_record(record, title=str(record.get("title") or "intro"), text=intro, index=0, start_char=0, end_char=matches[0].start()))

    for idx, match in enumerate(matches):
        title = match.group(2 if pattern is HEADING_PATTERN else 1).strip()
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        section_text = text[start:end].strip()
        if section_text:
            parents.append(parent_record(record, title=title, text=section_text, index=len(parents), start_char=start, end_char=end))

    return parents


def parent_record(record: dict[str, Any], *, title: str, text: str, index: int, start_char: int, end_char: int) -> dict[str, Any]:
    return {
        "parent_id": f"{record['id']}::parent::{index:04d}",
        "source_id": record["id"],
        "source_type": record.get("source_type"),
        "source_path": record.get("source_path"),
        "source_title": record.get("title"),
        "parent_title": title,
        "parent_text": text,
        "parent_index": index,
        "parent_start_char": start_char,
        "parent_end_char": end_char,
        "metadata": record.get("metadata", {}),
    }


def child_chunks(parent: dict[str, Any], *, child_size_words: int, child_overlap_words: int) -> list[dict[str, Any]]:
    text = parent["parent_text"]
    tokens = list(TOKEN_PATTERN.finditer(text))
    if not tokens:
        return []
    step = max(1, child_size_words - child_overlap_words)
    chunks = []
    for chunk_index, start_token in enumerate(range(0, len(tokens), step)):
        token_slice = tokens[start_token : start_token + child_size_words]
        if not token_slice:
            continue
        start_char = token_slice[0].start()
        end_char = token_slice[-1].end()
        child_text = text[start_char:end_char].strip()
        if not child_text:
            continue
        chunks.append(
            {
                "chunk_id": f"{parent['parent_id']}::child-{child_size_words}-{child_overlap_words}::{chunk_index:04d}",
                "parent_id": parent["parent_id"],
                "source_id": parent["source_id"],
                "source_type": parent["source_type"],
                "source_path": parent["source_path"],
                "title": parent["source_title"],
                "parent_title": parent["parent_title"],
                "text": child_text,
                "parent_text": parent["parent_text"],
                "metadata": parent["metadata"],
                "chunk_strategy": "parent_child_sections",
                "parent_index": parent["parent_index"],
                "chunk_index": chunk_index,
                "start_char": parent["parent_start_char"] + start_char,
                "end_char": parent["parent_start_char"] + end_char,
                "start_word": start_token,
                "end_word": start_token + len(token_slice),
            }
        )
        if start_token + child_size_words >= len(tokens):
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
    parents = [parent for record in records for parent in split_parents(record)]
    chunks = [
        chunk
        for parent in parents
        for chunk in child_chunks(
            parent,
            child_size_words=args.child_size_words,
            child_overlap_words=args.child_overlap_words,
        )
    ]
    write_jsonl(args.output_path, chunks)
    manifest = ChunkManifest(
        strategy="parent_child_sections",
        created_at=datetime.now(UTC).isoformat(),
        source_path=args.corpus_path.as_posix(),
        output_path=args.output_path.as_posix(),
        source_documents=len(records),
        parents=len(parents),
        chunks=len(chunks),
        child_size_words=args.child_size_words,
        child_overlap_words=args.child_overlap_words,
        sha256=sha256_file(args.output_path),
    )
    args.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_path.write_text(json.dumps(asdict(manifest), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"parents": len(parents), "chunks": len(chunks), "sha256": manifest.sha256}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
