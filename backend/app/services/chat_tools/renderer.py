"""Render tool results into compact assistant-facing text."""

from app.api.schemas.chat import ChatToolResult


def render_tool_answer(tool_results: list[ChatToolResult]) -> str:
    lines = ["Here is the tool output for this issue:"]
    for result in tool_results:
        if result.name == "memory.write":
            if result.status == "ok":
                lines.append("- Memory saved explicitly.")
            else:
                error = result.metadata.get("error", "memory write failed")
                lines.append(f"- Memory was not saved: {error}")
            continue

        if result.status != "ok":
            lines.append(f"- {result.name}: unavailable right now.")
            continue

        if result.name == "classifier.classify":
            label = result.metadata.get("label", "unknown")
            confidence = result.metadata.get("confidence", 0.0)
            lines.append(f"- Classification: **{label}** ({confidence:.1%} confidence).")
        elif result.name == "ner.extract":
            grouped = result.metadata.get("grouped", {})
            if grouped:
                compact = "; ".join(
                    f"{kind}: {', '.join(values[:5])}"
                    for kind, values in grouped.items()
                    if values
                )
                lines.append(f"- Extracted entities: {compact}.")
            else:
                lines.append("- Extracted entities: none found.")
        elif result.name == "summarizer.summarize":
            summary = result.metadata.get("summary", "")
            risk = result.metadata.get("risk_level", "unknown")
            lines.append(f"- Summary: {summary}")
            lines.append(f"- Risk level: **{risk}**.")
    return "\n".join(lines)
