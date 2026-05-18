"""Shared dataset constants for the Week 7 issue-classification pipeline."""

SOURCE_REPO = "pandas-dev/pandas"
ISSUE_STATE = "closed"

TARGET_LABELS = ("bug", "feature", "docs", "question")

LABEL_TO_TARGET = {
    "bug": "bug",
    "enhancement": "feature",
    "docs": "docs",
    "usage question": "question",
}
