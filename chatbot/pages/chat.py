import os

import httpx
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

st.title("Chat")
st.caption("Ask project or maintainer questions. The backend will use RAG when available.")

use_rag = st.sidebar.checkbox("Use RAG retrieval", value=True)
allow_summarizer = st.sidebar.checkbox(
    "Allow LLM summarizer",
    value=False,
    help="Off by default because this can call OpenAI.",
)
allow_memory_write = st.sidebar.checkbox(
    "Allow explicit memory writes",
    value=False,
    help="Only used when your message asks the assistant to remember something.",
)
access_token = st.sidebar.text_input(
    "Access token",
    value=st.session_state.get("access_token", ""),
    type="password",
    help="Login page fills this automatically. You can paste a token manually for smoke tests.",
)
if access_token:
    st.session_state.access_token = access_token

current_user = st.session_state.get("current_user")
if current_user:
    st.sidebar.success(f"Signed in: {current_user['email']}")
elif allow_memory_write:
    st.sidebar.warning("Memory writes need login; unauthenticated writes will be blocked.")

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
        "messages": [
            {"role": item["role"], "content": item["content"]}
            for item in st.session_state.messages
        ],
        "use_rag": use_rag,
        "top_k": 5,
        "allow_summarizer": allow_summarizer,
        "allow_memory_write": allow_memory_write,
        "tools": ["auto"],
    }

    with st.chat_message("assistant"):
        with st.spinner("Calling maintainer tools…"):
            try:
                headers = {}
                if access_token:
                    headers["Authorization"] = f"Bearer {access_token}"
                response = httpx.post(
                    f"{API_BASE_URL}/chat",
                    json=payload,
                    headers=headers,
                    timeout=30.0,
                )
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
