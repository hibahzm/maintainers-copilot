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
    """Yield issue payloads by following GitHub's Link-header pagination."""
    query = urlencode(
        {
            "state": state,
            "per_page": 100,
            "sort": "created",
            "direction": "asc",
        }
    )
    url: str | None = f"{GITHUB_API_BASE}/repos/{repo}/issues?{query}"
    pages_seen = 0

    while url is not None and (max_pages is None or pages_seen < max_pages):
        payload, headers = _request_json(url)
        pages_seen += 1

        if not isinstance(payload, list):
            raise RuntimeError("GitHub returned an unexpected non-list issue response.")

        for issue in payload:
            if not isinstance(issue, dict):
                raise RuntimeError("GitHub returned an unexpected issue payload.")
            yield issue

        url = _next_link(headers.get("Link"))


def _request_json(url: str) -> tuple[Any, dict[str, str]]:
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
            return json.load(response), dict(response.headers.items())
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub request failed with HTTP {exc.code}: {detail}") from exc


def _next_link(link_header: str | None) -> str | None:
    """Return the URL marked rel=next from a GitHub Link header."""
    if not link_header:
        return None

    for part in link_header.split(","):
        url_part, *params = part.split(";")
        if any(param.strip() == 'rel="next"' for param in params):
            return url_part.strip()[1:-1]

    return None


def main() -> None:
    args = parse_args()
    issues = fetch_closed_issues(repo=args.repo, state=args.state, max_pages=args.max_pages)
    write_jsonl(args.output, issues)
    print(f"Wrote {len(issues)} closed issues to {args.output}.")


if __name__ == "__main__":
    main()
