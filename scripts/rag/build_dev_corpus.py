"""Build a small local RAG dev corpus from existing docs and held-out issues."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_DOCS_DIR = Path("docs")
DEFAULT_ISSUES_PATH = Path("data/test_200_balanced.jsonl")
DEFAULT_OUTPUT_PATH = Path("data/rag/raw/dev_corpus.jsonl")
DEFAULT_MANIFEST_PATH = Path("data/rag/corpus_manifest.json")


@dataclass(frozen=True)
class CorpusSource:
    source_type: str
    path: str
    documents: int
    note: str | None = None


@dataclass(frozen=True)
class CorpusManifest:
    corpus_name: str
    created_at: str
    description: str
    documents: int
    output_path: str
    sha256: str
    sources: list[CorpusSource]
    status: str = "generated"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS_DIR)
    parser.add_argument("--issues-path", type=Path, default=DEFAULT_ISSUES_PATH)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--issue-limit", type=int, default=40)
    return parser.parse_args()


def iter_doc_records(docs_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(docs_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            continue
        records.append(
            {
                "id": f"project-doc:{path.as_posix()}",
                "source_type": "project_doc",
                "source_path": path.as_posix(),
                "title": _first_heading(text) or path.stem.replace("_", " ").title(),
                "text": text,
                "metadata": {
                    "repo": "maintainers-copilot",
                    "format": "markdown",
                    "path": path.as_posix(),
                },
            }
        )
    return records


def iter_issue_records(path: Path, limit: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if len(records) >= limit:
                break
            if not line.strip():
                continue
            issue = json.loads(line)
            issue_id = str(issue.get("id") or f"issue:{issue.get('number')}")
            title = str(issue.get("title") or "Untitled issue")
            body = str(issue.get("body") or "")
            label = issue.get("target")
            text = f"# {title}\n\n{body}".strip()
            records.append(
                {
                    "id": f"github-issue:{issue_id}",
                    "source_type": "github_issue",
                    "source_path": str(issue.get("url") or issue_id),
                    "title": title,
                    "text": text,
                    "metadata": {
                        "repo": issue.get("repo"),
                        "number": issue.get("number"),
                        "label": label,
                        "created_at": issue.get("created_at"),
                        "closed_at": issue.get("closed_at"),
                        "url": issue.get("url"),
                        "held_out": True,
                        "has_maintainer_answer": False,
                    },
                }
            )
    return records


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


def write_manifest(path: Path, manifest: CorpusManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(manifest)
    payload["sources"] = [asdict(source) for source in manifest.sources]
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _first_heading(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or None
    return None


def main() -> None:
    args = parse_args()
    doc_records = iter_doc_records(args.docs_dir)
    issue_records = iter_issue_records(args.issues_path, args.issue_limit)
    records = doc_records + issue_records
    if not records:
        raise RuntimeError("No RAG corpus records were found. Check docs dir and local issue data paths.")

    write_jsonl(args.output_path, records)
    manifest = CorpusManifest(
        corpus_name="maintainers-copilot-rag-dev",
        created_at=datetime.now(UTC).isoformat(),
        description="Small local development corpus for Step 3 RAG. Raw/chunk/index files stay outside Git.",
        documents=len(records),
        output_path=args.output_path.as_posix(),
        sha256=sha256_file(args.output_path),
        sources=[
            CorpusSource(
                source_type="project_doc",
                path=args.docs_dir.as_posix(),
                documents=len(doc_records),
            ),
            CorpusSource(
                source_type="github_issue",
                path=args.issues_path.as_posix(),
                documents=len(issue_records),
                note="Held-out issue text only in the dev corpus; maintainer-answer comments are added in the full MinIO corpus.",
            ),
        ],
    )
    write_manifest(args.manifest_path, manifest)
    print(json.dumps({"documents": len(records), "sha256": manifest.sha256}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
