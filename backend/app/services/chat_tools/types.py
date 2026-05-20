"""Shared chat-tool type definitions."""

from typing import Literal

ChatToolName = Literal["auto", "rag", "classifier", "ner", "summarizer", "write_memory"]
