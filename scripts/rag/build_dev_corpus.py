"""Build a small local RAG dev corpus from existing docs and held-out issues."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_DOCS_DIR = Path("docs")
DEFAULT_ISSUES_PATH = Path("data/test_200_balanced.jsonl")
DEFAULT_OUTPUT_PATH = Path("data/rag/raw/dev_corpus.jsonl")
DEFAULT_MANIFEST_PATH = Path("data/rag/corpus_manifest.json")
DEFAULT_GOLDEN_PATH = Path("evals/golden_rag.json")
DEFAULT_DEV_ISSUES_PATH = Path("data/rag/dev_issue_sources.json")
DEFAULT_GITHUB_REPO = "pandas-dev/pandas"
GITHUB_ISSUE_SOURCE_PATTERN = re.compile(r"^github-issue:(?P<repo>[^#]+)#(?P<number>\d+)$")
TARGET_LABEL_MAP = {
    "bug": "bug",
    "enhancement": "feature",
    "docs": "docs",
    "usage question": "question",
}


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
    parser.add_argument("--golden-path", type=Path, default=DEFAULT_GOLDEN_PATH)
    parser.add_argument("--dev-issues-path", type=Path, default=DEFAULT_DEV_ISSUES_PATH)
    parser.add_argument("--github-repo", default=DEFAULT_GITHUB_REPO)
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
                    "id": issue_id if issue_id.startswith("github-issue:") else f"github-issue:{issue_id}",
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


def iter_dev_github_issue_records(dev_issues_path: Path, *, limit: int) -> list[dict[str, Any]]:
    if not dev_issues_path.exists():
        return []
    payload = json.loads(dev_issues_path.read_text(encoding="utf-8"))
    refs = payload.get("issues", [])[:limit]
    return [github_issue_record(str(ref["repo"]), int(ref["number"]), label=ref.get("label")) for ref in refs]


def github_issue_record(repo: str, number: int, *, label: str | None = None) -> dict[str, Any]:
    issue = fetch_github_issue(repo, number)
    title = str(issue.get("title") or "Untitled issue")
    body = str(issue.get("body") or "")
    labels = [label.get("name", "") for label in issue.get("labels", []) if isinstance(label, dict)]
    target_label = label or next((TARGET_LABEL_MAP[label_name] for label_name in labels if label_name in TARGET_LABEL_MAP), None)
    text = f"# {title}\n\n{body}".strip()
    return {
        "id": f"github-issue:{repo}#{number}",
        "source_type": "github_issue",
        "source_path": str(issue.get("html_url") or f"https://github.com/{repo}/issues/{number}"),
        "title": title,
        "text": text,
        "metadata": {
            "repo": repo,
            "number": number,
            "label": target_label,
            "created_at": issue.get("created_at"),
            "closed_at": issue.get("closed_at"),
            "url": issue.get("html_url"),
            "held_out": True,
            "has_maintainer_answer": False,
            "source": "github_api_dev_issue_sources",
        },
    }


def iter_golden_github_issue_records(golden_path: Path, *, repo: str, limit: int) -> list[dict[str, Any]]:
    """Fetch the small golden-set issue corpus when local JSONL data is absent.

    This keeps a fresh Colab clone reproducible without committing row-level issue
    datasets to Git. The public GitHub API is enough because we fetch only the
    issue records referenced by `evals/golden_rag.json`.
    """
    if not golden_path.exists():
        return []

    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    issue_numbers: list[int] = []
    seen: set[int] = set()
    for record in golden:
        for source_id in record.get("ground_truth_source_ids", []):
            match = GITHUB_ISSUE_SOURCE_PATTERN.match(str(source_id))
            if not match or match.group("repo") != repo:
                continue
            number = int(match.group("number"))
            if number not in seen:
                seen.add(number)
                issue_numbers.append(number)
            if len(issue_numbers) >= limit:
                break
        if len(issue_numbers) >= limit:
            break

    return [github_issue_record(repo, number) for number in issue_numbers]


def fetch_github_issue(repo: str, number: int) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{repo}/issues/{number}"
    request = Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "maintainers-copilot-rag-corpus-builder"})
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"GitHub issue fetch failed for {repo}#{number}: HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"GitHub issue fetch failed for {repo}#{number}: {exc.reason}") from exc


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
    issue_source_path = args.issues_path.as_posix()
    issue_source_note = "Held-out issue text only in the dev corpus; maintainer-answer comments are added in the full MinIO corpus."
    if not issue_records:
        issue_records = iter_dev_github_issue_records(args.dev_issues_path, limit=args.issue_limit)
        issue_source_path = args.dev_issues_path.as_posix()
        if issue_records:
            issue_source_note = "Fetched public GitHub issue records from tracked issue IDs because the local JSONL issue dataset was absent."
    if not issue_records:
        issue_records = iter_golden_github_issue_records(args.golden_path, repo=args.github_repo, limit=args.issue_limit)
        issue_source_path = args.golden_path.as_posix()
        if issue_records:
            issue_source_note = "Fetched public GitHub issue records referenced by the RAG golden set because no local/dev issue list was available."
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
                path=issue_source_path,
                documents=len(issue_records),
                note=issue_source_note,
            ),
        ],
    )
    write_manifest(args.manifest_path, manifest)
    print(json.dumps({"documents": len(records), "sha256": manifest.sha256}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
