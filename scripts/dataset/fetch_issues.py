"""Fetch closed issues from the fixed Week 7 GitHub repository."""

import argparse
import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from scripts.dataset.constants import ISSUE_STATE, SOURCE_REPO
from scripts.dataset.io import write_jsonl

GITHUB_API_BASE = "https://api.github.com"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=SOURCE_REPO)
    parser.add_argument("--state", default=ISSUE_STATE)
    parser.add_argument("--output", type=Path, default=Path("data/raw_issues.jsonl"))
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional safety cap for dry runs; omit to fetch every page.",
    )
    return parser.parse_args()


def fetch_closed_issues(
    repo: str,
    state: str = ISSUE_STATE,
    max_pages: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch GitHub issues, excluding pull requests returned by the issues endpoint."""
    issues: list[dict[str, Any]] = []
    for issue in iter_issue_pages(repo=repo, state=state, max_pages=max_pages):
        if "pull_request" in issue:
            continue
        issue["repo_full_name"] = repo
        issues.append(issue)
    return issues


def iter_issue_pages(
    repo: str,
    state: str,
    max_pages: int | None,
) -> Iterator[dict[str, Any]]:
    """Yield issue payloads page by page from GitHub's REST API."""
    page = 1
    while max_pages is None or page <= max_pages:
        query = urlencode(
            {
                "state": state,
                "per_page": 100,
                "page": page,
                "sort": "created",
                "direction": "asc",
            }
        )
        url = f"{GITHUB_API_BASE}/repos/{repo}/issues?{query}"
        payload = _request_json(url)
        if not payload:
            break

        if not isinstance(payload, list):
            raise RuntimeError("GitHub returned an unexpected non-list issue response.")

        for issue in payload:
            if not isinstance(issue, dict):
                raise RuntimeError("GitHub returned an unexpected issue payload.")
            yield issue

        page += 1


def _request_json(url: str) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "maintainers-copilot-dataset-pipeline",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers)
    try:
        with urlopen(request) as response:
            return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"GitHub request failed with HTTP {exc.code}.") from exc


def main() -> None:
    args = parse_args()
    issues = fetch_closed_issues(repo=args.repo, state=args.state, max_pages=args.max_pages)
    write_jsonl(args.output, issues)
    print(f"Wrote {len(issues)} closed issues to {args.output}.")


if __name__ == "__main__":
    main()
