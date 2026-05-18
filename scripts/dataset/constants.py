"""Shared dataset constants for the Week 7 issue-classification pipeline."""

SOURCE_REPO = "fastapi/fastapi"
ISSUE_STATE = "closed"

TARGET_LABELS = ("bug", "feature", "docs", "question")

# FastAPI already uses the four assignment-aligned labels directly.
LABEL_TO_TARGET = {
    "bug": "bug",
    "feature": "feature",
    "docs": "docs",
    "question": "question",
}
