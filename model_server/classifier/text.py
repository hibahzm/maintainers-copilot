"""Shared text preprocessing for issue-classification experiments."""


def compose_issue_text(title: str | None, body: str | None) -> str:
    """Join issue title and body with a stable, model-agnostic format."""
    clean_title = (title or "").strip()
    clean_body = (body or "").strip()
    return f"{clean_title}\n\n{clean_body}".strip()
