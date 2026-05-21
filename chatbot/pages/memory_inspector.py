from html import escape

import httpx
import streamlit as st

from ui import API_BASE_URL, auth_headers, render_user_sidebar, require_login

require_login()
render_user_sidebar()

st.markdown(
    """
    <div class="mc-page-header">
      <div>
        <h1>Memory</h1>
        <p>Review long-term memories created through explicit chat requests.</p>
      </div>
      <div class="mc-header-actions">
        <span class="mc-pill neutral">Explicit writes only</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.write("")

left, right = st.columns([0.7, 0.3], gap="large")

with right:
    st.markdown("### Controls")
    limit = st.slider("Memories to load", min_value=1, max_value=100, value=50)
    refresh = st.button("Refresh memories", type="primary", use_container_width=True)

if refresh or "memory_items" not in st.session_state:
    try:
        response = httpx.get(
            f"{API_BASE_URL}/memory",
            params={"limit": limit},
            headers=auth_headers(),
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

with left:
    if not items:
        st.info("No long-term memories saved yet.")
        st.stop()

    for item in items:
        content = escape(str(item["content"]))
        memory_id = escape(str(item["id"]))
        memory_type = escape(str(item["memory_type"]))
        created_at = escape(str(item["created_at"]))
        st.markdown(
            f"""
            <div class="mc-card">
              <div class="mc-pill-row">
                <span class="mc-pill">{memory_type}</span>
                <span class="mc-pill neutral">{created_at}</span>
              </div>
              <p style="margin-top:.75rem">{content}</p>
              <p class="mc-caption">Memory ID: {memory_id}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
