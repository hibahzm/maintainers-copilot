import os

import httpx
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

st.title("Chat")
st.caption("Ask project or maintainer questions. The backend will use RAG when available.")

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("citations"):
            st.caption("Citations: " + ", ".join(message["citations"]))

prompt = st.chat_input("Ask about the project, a maintainer workflow, or retrieved issue context…")
if prompt:
    user_message = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_message)
    with st.chat_message("user"):
        st.markdown(prompt)

    payload = {
        "conversation_id": st.session_state.conversation_id,
        "messages": [{"role": item["role"], "content": item["content"]} for item in st.session_state.messages],
        "use_rag": True,
        "top_k": 5,
    }

    with st.chat_message("assistant"):
        with st.spinner("Calling maintainer tools…"):
            try:
                response = httpx.post(f"{API_BASE_URL}/chat", json=payload, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                assistant_message = data["message"]
                citations = data.get("citations", [])
                st.session_state.conversation_id = data.get("conversation_id")
                st.markdown(assistant_message["content"])
                if citations:
                    st.caption("Citations: " + ", ".join(citations))
                with st.expander("Tool details", expanded=False):
                    st.json(data.get("tool_results", []))
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": assistant_message["content"],
                        "citations": citations,
                    }
                )
            except httpx.HTTPError as exc:
                error = f"Chat request failed: {exc}"
                st.error(error)
                st.session_state.messages.append({"role": "assistant", "content": error})
