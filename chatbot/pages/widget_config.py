import json
import os

import httpx
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

st.title("Widget Config")
st.caption("Admin-only widget configuration surface.")

access_token = st.session_state.get("access_token", "")
current_user = st.session_state.get("current_user")

if not access_token:
    st.warning("Log in with an admin account first.")
    st.stop()
if current_user:
    st.info(f"Signed in: {current_user['email']} ({current_user['role']})")
    if current_user.get("role") != "admin":
        st.warning("This page requires an admin token.")

headers = {"Authorization": f"Bearer {access_token}"}

with st.form("widget-config-form"):
    widget_id = st.text_input("Widget ID", value="maintainers-copilot")
    allowed_origins_text = st.text_area(
        "Allowed origins, one per line",
        value="http://localhost:5173\nhttp://localhost:8501",
    )
    greeting = st.text_area("Greeting", value="How can I help maintainers today?")
    accent_color = st.text_input("Accent color", value="#2563eb")
    mode = st.selectbox("Theme mode", ["light", "dark"], index=0)
    enabled_tools = st.multiselect(
        "Enabled tools",
        ["rag_search", "classify_issue", "extract_entities", "summarize_issue"],
        default=["rag_search"],
    )
    submitted = st.form_submit_button("Save widget config", type="primary")

if submitted:
    payload = {
        "widget_id": widget_id,
        "allowed_origins": [
            origin.strip() for origin in allowed_origins_text.splitlines() if origin.strip()
        ],
        "theme": {"mode": mode, "accent_color": accent_color},
        "greeting": greeting,
        "enabled_tools": enabled_tools,
    }
    try:
        response = httpx.put(
            f"{API_BASE_URL}/widget/admin/config/{widget_id}",
            json=payload,
            headers=headers,
            timeout=20.0,
        )
        response.raise_for_status()
        st.success("Widget config saved.")
        st.json(response.json())
    except httpx.HTTPStatusError as exc:
        detail = exc.response.json().get("detail", exc.response.text)
        st.error(f"Could not save widget config: {detail}")
    except httpx.HTTPError as exc:
        st.error(f"Widget config request failed: {exc}")

st.divider()
st.subheader("Existing configs")

if st.button("Load configs"):
    try:
        response = httpx.get(
            f"{API_BASE_URL}/widget/admin/configs",
            headers=headers,
            timeout=20.0,
        )
        response.raise_for_status()
        configs = response.json()
        if configs:
            for config in configs:
                with st.expander(config["widget_id"]):
                    st.code(json.dumps(config, indent=2), language="json")
        else:
            st.info("No widget configs saved yet.")
    except httpx.HTTPStatusError as exc:
        detail = exc.response.json().get("detail", exc.response.text)
        st.error(f"Could not load widget configs: {detail}")
    except httpx.HTTPError as exc:
        st.error(f"Widget config request failed: {exc}")
