import os

import httpx
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

st.title("Memory Inspector")
st.caption("Review long-term memories saved for the signed-in user.")

access_token = st.session_state.get("access_token", "")
current_user = st.session_state.get("current_user")

if not access_token:
    st.warning("Log in first to inspect your memories.")
    st.stop()

if current_user:
    st.success(f"Signed in: {current_user['email']} ({current_user['role']})")

limit = st.slider("Memories to load", min_value=1, max_value=100, value=50)

if st.button("Refresh memories", type="primary") or "memory_items" not in st.session_state:
    try:
        response = httpx.get(
            f"{API_BASE_URL}/memory",
            params={"limit": limit},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=20.0,
        )
        response.raise_for_status()
        st.session_state.memory_items = response.json().get("items", [])
    except httpx.HTTPStatusError as exc:
        detail = exc.response.json().get("detail", exc.response.text)
        st.error(f"Could not load memories: {detail}")
        st.stop()
    except httpx.HTTPError as exc:
        st.error(f"Memory request failed: {exc}")
        st.stop()

items = st.session_state.get("memory_items", [])
if not items:
    st.info("No long-term memories saved yet.")
    st.stop()

for item in items:
    with st.expander(f"{item['memory_type']} · {item['created_at']}"):
        st.write(item["content"])
        st.caption(f"Memory ID: {item['id']}")
