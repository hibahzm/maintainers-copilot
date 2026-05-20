"""Tool selection heuristics for chat turns."""

from app.services.chat_tools.types import ChatToolName


def select_tools(
    text: str,
    *,
    tools: list[ChatToolName],
    use_rag: bool,
    allow_summarizer: bool,
    allow_memory_write: bool,
) -> set[str]:
    explicit = {tool for tool in tools if tool != "auto"}
    if explicit:
        return {tool for tool in explicit if tool != "rag"}

    lowered = text.lower()
    selected: set[str] = set()
    if any(word in lowered for word in ("classify", "classification", "label", "triage")):
        selected.add("classifier")
    if any(word in lowered for word in ("ner", "entity", "entities", "extract")):
        selected.add("ner")
    summary_keywords = ("summarize", "summary", "tl;dr", "tldr")
    if allow_summarizer and any(word in lowered for word in summary_keywords):
        selected.add("summarizer")
    if allow_memory_write and any(
        phrase in lowered for phrase in ("remember", "save this memory", "write memory")
    ):
        selected.add("write_memory")

    if selected:
        return selected
    return set() if use_rag else selected
