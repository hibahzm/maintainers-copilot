from html import escape

import httpx
import streamlit as st

from ui import API_BASE_URL, auth_headers, parse_sse_lines, render_user_sidebar, require_login


def _tool_label(name: str) -> str:
    labels = {
        "rag.query": "Retrieval",
        "classifier.classify": "Classifier",
        "ner.extract": "Entities",
        "summarizer.summarize": "Summarizer",
        "memory.write": "Memory",
    }
    return labels.get(name, name)


def _tool_detail(tool: dict) -> str:
    metadata = tool.get("metadata") or {}
    if tool.get("name") == "rag.query":
        chunks = tool.get("chunks") or []
        return f"{len(chunks)} chunks returned"
    if tool.get("name") == "classifier.classify":
        label = metadata.get("label", "unknown")
        confidence = metadata.get("confidence")
        if isinstance(confidence, (int, float)):
            return f"{label} at {confidence:.0%}"
        return str(label)
    if tool.get("name") == "ner.extract":
        grouped = metadata.get("grouped") or {}
        count = sum(len(values) for values in grouped.values() if isinstance(values, list))
        return f"{count} entities found"
    if tool.get("name") == "summarizer.summarize":
        return str(metadata.get("risk_level") or "summary ready")
    if tool.get("name") == "memory.write":
        return "explicit memory write"
    return str(tool.get("status") or "ok")


def _render_run_detail(tool_results: list[dict], citations: list[str]) -> None:
    st.markdown("#### Run detail")
    if not tool_results:
        st.info("No tool calls recorded for the latest turn.")
    for tool in tool_results:
        status = tool.get("status", "unknown")
        label = escape(_tool_label(str(tool.get("name", "tool"))))
        detail = escape(_tool_detail(tool))
        safe_status = escape(str(status))
        st.markdown(
            f"""
            <div class="mc-run-card">
              <strong>{label}</strong>
              <span>Status: {safe_status} - {detail}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("#### Sources")
    if citations:
        for citation in citations:
            st.markdown(f'<div class="mc-source">{escape(str(citation))}</div>', unsafe_allow_html=True)
    else:
        st.caption("No citations returned yet.")


require_login()
render_user_sidebar()

st.markdown(
    """
    <div class="mc-page-header">
      <div>
        <h1>Copilot chat</h1>
        <p>Internal version of the same copilot used by the public widget, with login, citations, and tool evidence.</p>
      </div>
      <div class="mc-header-actions">
        <span class="mc-pill">Authenticated</span>
        <span class="mc-pill info">Same backend as widget</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.write("")

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_tool_results" not in st.session_state:
    st.session_state.last_tool_results = []
if "last_citations" not in st.session_state:
    st.session_state.last_citations = []

with st.sidebar:
    st.divider()
    st.markdown("### Tool policy")
    use_rag = st.toggle("Use retrieval", value=True)
    top_k = st.slider("Retrieved chunks", min_value=1, max_value=10, value=5)
    allow_summarizer = st.toggle(
        "Allow summarizer",
        value=False,
        help="The summarizer may call the configured LLM-backed model.",
    )
    allow_memory_write = st.toggle(
        "Allow explicit memory saves",
        value=False,
        help="Memory writes still require the user to ask for a memory to be saved.",
    )
    st.divider()
    st.markdown("### Retrieval status")
    try:
        status_response = httpx.get(f"{API_BASE_URL}/rag/status", timeout=10.0)
        status_response.raise_for_status()
        rag_status = status_response.json()
        if rag_status.get("ready"):
            st.success(
                f"{rag_status.get('embedded_chunks', 0)} embedded chunks across "
                f"{rag_status.get('sources', 0)} sources."
            )
        else:
            st.warning("RAG index is empty. Restart the stack and watch API startup logs.")
    except httpx.HTTPError:
        st.warning("RAG status is unavailable.")
    st.divider()
    if st.button("Start new chat", use_container_width=True):
        st.session_state.conversation_id = None
        st.session_state.messages = []
        st.session_state.last_tool_results = []
        st.session_state.last_citations = []
        st.rerun()

quick_prompt = None
quick_cols = st.columns(3)
examples = [
    (
        "RAG context",
        "Use RAG to explain what context we have for pandas read_csv empty-file crashes.",
    ),
    (
        "Classify issue",
        "Classify this issue: read_csv crashes on empty CSV with ValueError on Python 3.12.",
    ),
    (
        "Extract entities",
        "Extract entities from: pandas 2.2 raises ValueError in pandas/io/parsers.py on Windows.",
    ),
]
for col, (label, example) in zip(quick_cols, examples, strict=True):
    if col.button(label, use_container_width=True):
        quick_prompt = example

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("citations"):
            st.caption("Sources: " + ", ".join(message["citations"]))

with st.expander("Latest run detail", expanded=bool(st.session_state.last_tool_results)):
    _render_run_detail(st.session_state.last_tool_results, st.session_state.last_citations)

typed_prompt = st.chat_input("Ask about an issue, release, docs gap, or maintainer decision")
prompt = typed_prompt or quick_prompt

if prompt:
    user_message = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_message)
    with st.chat_message("user"):
        st.markdown(prompt)

    payload = {
        "conversation_id": st.session_state.conversation_id,
        "messages": [
            {"role": item["role"], "content": item["content"]}
            for item in st.session_state.messages
        ],
        "use_rag": use_rag,
        "top_k": top_k,
        "allow_summarizer": allow_summarizer,
        "allow_memory_write": allow_memory_write,
        "tools": ["auto"],
    }

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        status_placeholder = st.empty()

        assistant_text = ""
        citations: list[str] = []
        tool_results: list[dict] = []
        try:
            status_placeholder.info("Processing request...")

            with httpx.stream(
                "POST",
                f"{API_BASE_URL}/chat/stream",
                json=payload,
                headers=auth_headers(),
                timeout=60.0,
            ) as response:
                response.raise_for_status()

                for event, data in parse_sse_lines(response.iter_lines()):
                    if event == "metadata":
                        st.session_state.conversation_id = data.get("conversation_id")
                        citations = data.get("citations", [])
                    elif event == "tool_result":
                        tool_results.append(data)
                        status_placeholder.info(f"Using {_tool_label(data.get('name', 'tool'))}...")
                    elif event == "delta":
                        status_placeholder.empty()
                        assistant_text += data.get("content", "")
                        response_placeholder.markdown(assistant_text + " |")
                    elif event == "final":
                        st.session_state.conversation_id = data.get("conversation_id")
                        assistant_text = data.get("message", {}).get("content", assistant_text)
                        citations = data.get("citations", citations)
                        tool_results = data.get("tool_results", tool_results)
                    elif event == "error":
                        raise RuntimeError(data.get("message", "Chat request failed."))

            status_placeholder.empty()
            response_placeholder.markdown(assistant_text)

            st.session_state.last_tool_results = tool_results
            st.session_state.last_citations = citations
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": assistant_text,
                    "citations": citations,
                }
            )
            st.rerun()
        except (httpx.HTTPError, RuntimeError) as exc:
            status_placeholder.empty()
            error = f"Chat request failed: {exc}"
            st.error(error)
            st.session_state.last_tool_results = []
            st.session_state.last_citations = []
            st.session_state.messages.append({"role": "assistant", "content": error})
