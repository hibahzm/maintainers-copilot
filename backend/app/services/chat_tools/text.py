"""Text normalization helpers for chat tools."""


def split_issue_text(text: str) -> tuple[str, str]:
    cleaned_lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if not cleaned_lines:
        return "Untitled issue", ""

    title = cleaned_lines[0]
    instruction_prefixes = (
        "classify this issue:",
        "classify:",
        "label this issue:",
        "label:",
        "triage this issue:",
        "extract entities:",
        "summarize this issue:",
        "summarize:",
    )
    lowered_title = title.lower()
    for prefix in instruction_prefixes:
        if lowered_title.startswith(prefix):
            title = title[len(prefix) :].strip() or "Untitled issue"
            break

    body = "\n".join(cleaned_lines[1:])
    return title[:300], body


def memory_content(text: str) -> str:
    lowered = text.lower()
    for prefix in ("remember that", "remember:", "save this memory:", "write memory:"):
        if lowered.startswith(prefix):
            return text[len(prefix) :].strip()
    return text.strip()
