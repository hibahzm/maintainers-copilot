import json

import httpx
import streamlit as st

from ui import (
    API_BASE_URL,
    PUBLIC_API_BASE_URL,
    TOOL_OPTIONS,
    auth_headers,
    render_user_sidebar,
    require_admin,
)

admin = require_admin()
render_user_sidebar()

st.markdown(
    """
    <div class="mc-page-header">
      <div>
        <h1>Widget config</h1>
        <p>Control the public React widget: origins, theme, greeting, and allowed tools.</p>
      </div>
      <div class="mc-header-actions">
        <span class="mc-pill">Admin only</span>
        <span class="mc-pill neutral">Runtime config</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.write("")

default_origins = "\n".join(
    [
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
)

with st.form("widget-config-form"):
    st.markdown("### Public widget")
    widget_id = st.text_input("Widget ID", value="maintainers-copilot")
    allowed_origins_text = st.text_area(
        "Allowed origins",
        value=default_origins,
        height=170,
        help="One origin per line. Add the real host origin here before embedding the widget.",
    )
    greeting = st.text_area(
        "Greeting",
        value="Ask about triage, project context, or an issue you are trying to route.",
        height=90,
    )

    theme_cols = st.columns(2)
    with theme_cols[0]:
        accent_color = st.color_picker("Accent color", value="#0891b2")
    with theme_cols[1]:
        mode = st.selectbox("Theme mode", ["light", "dark"], index=0)

    selected_tool_labels = st.multiselect(
        "Tools widget visitors can use",
        list(TOOL_OPTIONS.keys()),
        default=["RAG search", "Issue classifier", "Entity extractor"],
        help="Disabling a tool prevents the public widget endpoint from requesting it.",
    )

    submitted = st.form_submit_button("Save widget config", type="primary")

st.markdown("### Surface map")
st.markdown(
    """
    <div class="mc-port-grid">
      <div class="mc-port">
        <code>8501</code>
        <p class="mc-caption">Internal logged-in workspace.</p>
      </div>
      <div class="mc-port">
        <code>4173</code>
        <p class="mc-caption">Public React widget surface.</p>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.write("")
st.markdown("### Install snippet")
st.code(
    f"""<script
  src="{PUBLIC_API_BASE_URL}/widget.js"
  data-widget-id="maintainers-copilot"
  data-widget-url="http://localhost:4173"
  data-api-base="{PUBLIC_API_BASE_URL}"
  data-label="Ask copilot"
></script>""",
    language="html",
)

if submitted:
    payload = {
        "widget_id": widget_id,
        "allowed_origins": [
            origin.strip() for origin in allowed_origins_text.splitlines() if origin.strip()
        ],
        "theme": {"mode": mode, "accent_color": accent_color},
        "greeting": greeting,
        "enabled_tools": [TOOL_OPTIONS[label] for label in selected_tool_labels],
    }
    try:
        response = httpx.put(
            f"{API_BASE_URL}/widget/admin/config/{widget_id}",
            json=payload,
            headers=auth_headers(),
            timeout=20.0,
        )
        response.raise_for_status()
        st.success("Widget config saved.")
    except httpx.HTTPStatusError as exc:
        detail = exc.response.json().get("detail", exc.response.text)
        st.error(f"Could not save widget config: {detail}")
    except httpx.HTTPError as exc:
        st.error(f"Widget config request failed: {exc}")

st.divider()
st.markdown("### Existing configs")
try:
    response = httpx.get(
        f"{API_BASE_URL}/widget/admin/configs",
        headers=auth_headers(),
        timeout=20.0,
    )
    response.raise_for_status()
    configs = response.json()
except httpx.HTTPStatusError as exc:
    detail = exc.response.json().get("detail", exc.response.text)
    st.error(f"Could not load widget configs: {detail}")
    st.stop()
except httpx.HTTPError as exc:
    st.error(f"Widget config request failed: {exc}")
    st.stop()

if not configs:
    st.info("No widget configs saved yet.")
else:
    for config in configs:
        with st.expander(config["widget_id"], expanded=config["widget_id"] == "maintainers-copilot"):
            st.code(json.dumps(config, indent=2), language="json")

st.caption(f"Admin: {admin['email']}")
