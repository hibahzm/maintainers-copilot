import json
import os
from collections.abc import Iterable, Iterator

import httpx
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
PUBLIC_API_BASE_URL = os.getenv("PUBLIC_API_BASE_URL", "http://localhost:8000").rstrip("/")

TOOL_OPTIONS = {
    "RAG search": "rag_search",
    "Issue classifier": "classify_issue",
    "Entity extractor": "extract_entities",
    "Issue summarizer": "summarize_issue",
}


def init_auth_state() -> None:
    if "access_token" not in st.session_state:
        st.session_state.access_token = ""
    if "current_user" not in st.session_state:
        st.session_state.current_user = None


def inject_app_styles() -> None:
    st.markdown(
        """
        <style>
          :root {
            --mc-bg: #f3f8fb;
            --mc-ink: #164e63;
            --mc-panel: #ffffff;
            --mc-panel-soft: #f6f7fb;
            --mc-text: #111827;
            --mc-muted: #667085;
            --mc-line: #dde2eb;
            --mc-line-strong: #b9c2d0;
            --mc-accent: #0891b2;
            --mc-accent-strong: #0e7490;
            --mc-accent-soft: #ecfeff;
            --mc-info: #0f766e;
            --mc-warning: #b45309;
            --mc-danger: #be123c;
            --mc-success: #059669;
            --mc-radius: 8px;
          }

          .stApp {
            background: var(--mc-bg);
            color: var(--mc-text);
          }

          .block-container {
            max-width: 1120px;
            padding-left: clamp(.8rem, 2vw, 1.5rem);
            padding-right: clamp(.8rem, 2vw, 1.5rem);
            padding-top: 1.25rem;
            padding-bottom: 2rem;
          }

          [data-testid="stSidebar"] {
            background: #111827;
            border-right: 1px solid rgba(255, 255, 255, 0.08);
          }

          [data-testid="stSidebar"] * {
            color: #e5edf7 !important;
          }

          [data-testid="stSidebar"] div[role="separator"] {
            border-color: rgba(226, 232, 240, 0.14);
          }

          [data-testid="stSidebar"] div.stButton > button {
            border-color: rgba(255, 255, 255, 0.18);
            background: rgba(255, 255, 255, 0.08);
            color: #ffffff !important;
          }

          [data-testid="stSidebar"] div.stButton > button *,
          [data-testid="stSidebar"] div.stButton > button p {
            color: #ffffff !important;
          }

          [data-testid="stSidebar"] div.stButton > button:hover {
            border-color: rgba(255, 255, 255, 0.34);
            background: rgba(255, 255, 255, 0.14);
          }

          h1, h2, h3, h4, h5, h6, p, label, span, div {
            color: inherit;
          }

          h1 {
            font-size: 2rem !important;
            line-height: 1.12 !important;
            letter-spacing: 0 !important;
            color: var(--mc-ink);
          }

          h2, h3 {
            letter-spacing: 0 !important;
            color: var(--mc-ink);
          }

          .mc-page-header {
            display: flex;
            flex-wrap: wrap;
            align-items: flex-start;
            justify-content: space-between;
            gap: 1rem;
            border: 1px solid var(--mc-line);
            border-radius: var(--mc-radius);
            padding: 1.1rem 1.2rem;
            background: var(--mc-panel);
            box-shadow: none;
          }

          .mc-page-header > div {
            min-width: 0;
          }

          .mc-page-header h1 {
            margin: 0 0 .35rem;
            font-size: 2rem !important;
            line-height: 1.1 !important;
            overflow-wrap: anywhere;
          }

          .mc-page-header p,
          .mc-caption {
            margin: 0;
            color: var(--mc-muted);
            line-height: 1.55;
            font-size: .98rem;
          }

          .mc-header-actions {
            display: flex;
            flex-wrap: wrap;
            justify-content: flex-end;
            gap: .5rem;
          }

          .mc-card {
            border: 1px solid var(--mc-line);
            border-radius: var(--mc-radius);
            padding: 1rem;
            background: var(--mc-panel);
            box-shadow: none;
          }

          .mc-card h3 {
            margin: 0 0 .4rem;
            font-size: 1rem;
          }

          .mc-card,
          .mc-card p,
          .mc-caption,
          .mc-source {
            overflow-wrap: anywhere;
          }

          .mc-auth-shell {
            display: grid;
            grid-template-columns: minmax(0, 1.05fr) minmax(320px, .95fr);
            min-height: calc(100vh - 8rem);
            gap: 1rem;
            align-items: stretch;
          }

          .mc-auth-panel {
            border: 1px solid var(--mc-line);
            border-radius: var(--mc-radius);
            padding: clamp(1rem, 2vw, 1.45rem);
            background: var(--mc-panel);
            box-shadow: none;
          }

          .mc-auth-brand {
            display: flex;
            align-items: center;
            gap: .8rem;
            margin-bottom: 1.2rem;
          }

          .mc-mark {
            display: inline-grid;
            width: 42px;
            height: 42px;
            place-items: center;
            border-radius: var(--mc-radius);
            background: var(--mc-accent);
            color: #ffffff !important;
            font-weight: 900;
          }

          .mc-auth-title {
            margin: 0;
            font-size: 2.25rem;
            line-height: 1.05;
            color: var(--mc-ink);
          }

          .mc-auth-copy {
            color: var(--mc-muted);
            line-height: 1.65;
            max-width: 42rem;
          }

          .mc-auth-helper {
            border: 1px solid var(--mc-line);
            border-radius: var(--mc-radius);
            padding: .85rem;
            background: #ffffff;
            color: var(--mc-muted);
            line-height: 1.5;
            font-size: .92rem;
          }

          .mc-surface-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: .75rem;
            margin-top: 1.2rem;
          }

          .mc-surface {
            border: 1px solid var(--mc-line);
            border-radius: var(--mc-radius);
            padding: .85rem;
            background: var(--mc-panel-soft);
          }

          .mc-surface strong {
            display: block;
            margin-bottom: .25rem;
            color: var(--mc-ink);
          }

          .mc-surface span {
            display: block;
            color: var(--mc-muted);
            font-size: .88rem;
            line-height: 1.45;
          }

          .mc-pill-row {
            display: flex;
            flex-wrap: wrap;
            gap: .45rem;
            margin-top: .75rem;
          }

          .mc-pill {
            display: inline-flex;
            align-items: center;
            min-height: 30px;
            border: 1px solid #c7d2fe;
            border-radius: 999px;
            padding: .25rem .65rem;
            background: var(--mc-accent-soft);
            color: var(--mc-accent-strong) !important;
            font-size: .78rem;
            font-weight: 800;
          }

          .mc-pill.neutral {
            border-color: var(--mc-line);
            background: #f8fafc;
            color: #334155 !important;
          }

          .mc-pill.info {
            border-color: #99f6e4;
            background: #f0fdfa;
            color: #115e59 !important;
          }

          .mc-run-card {
            border: 1px solid var(--mc-line);
            border-radius: var(--mc-radius);
            padding: .85rem;
            background: var(--mc-panel);
            margin-bottom: .65rem;
          }

          .mc-run-card strong {
            display: block;
            color: var(--mc-ink);
            font-size: .92rem;
            margin-bottom: .2rem;
          }

          .mc-run-card span {
            display: block;
            color: var(--mc-muted);
            font-size: .84rem;
            line-height: 1.45;
          }

          .mc-source {
            border-left: 3px solid var(--mc-accent);
            padding: .55rem .75rem;
            background: #f8fafc;
            border-radius: 0 var(--mc-radius) var(--mc-radius) 0;
            margin-bottom: .5rem;
            color: #334155;
            font-size: .86rem;
          }

          .mc-port-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: .75rem;
          }

          .mc-port {
            border: 1px solid var(--mc-line);
            border-radius: var(--mc-radius);
            padding: .85rem;
            background: #ffffff;
          }

          .mc-port code {
            display: inline-block;
            margin-bottom: .4rem;
            color: #0f766e;
            font-weight: 800;
          }

          div.stButton > button,
          div.stDownloadButton > button {
            border-radius: var(--mc-radius);
            border: 1px solid var(--mc-line-strong);
            font-weight: 800;
            color: var(--mc-ink);
            background: #ffffff;
            min-height: 2.6rem;
            transition: border-color .18s ease, background .18s ease, color .18s ease;
          }

          div.stButton > button *,
          div.stDownloadButton > button * {
            color: inherit !important;
          }

          div.stButton > button:hover,
          div.stDownloadButton > button:hover {
            border-color: var(--mc-accent);
            color: var(--mc-accent-strong);
          }

          div.stButton > button[kind="primary"] {
            background: var(--mc-accent);
            color: #ffffff !important;
            border-color: var(--mc-accent);
          }

          div.stButton > button[kind="primary"] *,
          div.stButton > button[kind="primary"] p {
            color: #ffffff !important;
          }

          div.stButton > button[kind="primary"]:hover {
            background: var(--mc-accent-strong);
            color: #ffffff !important;
            border-color: var(--mc-accent-strong);
          }

          [data-testid="stSegmentedControl"] button {
            border-color: var(--mc-line) !important;
            color: var(--mc-ink) !important;
          }

          [data-testid="stSegmentedControl"] button[aria-pressed="true"] {
            border-color: var(--mc-accent) !important;
            background: var(--mc-accent-soft) !important;
            color: var(--mc-accent-strong) !important;
          }

          [data-testid="stChatMessage"] {
            border: 1px solid var(--mc-line);
            border-radius: var(--mc-radius);
            background: #ffffff;
            box-shadow: none;
          }

          [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
          [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li {
            color: var(--mc-text);
            line-height: 1.55;
          }

          textarea, input, .stTextInput input, .stTextArea textarea {
            color: var(--mc-text) !important;
            background: #ffffff !important;
            border-color: #cbd5e1 !important;
            border-radius: var(--mc-radius) !important;
          }

          .stChatInput textarea {
            color: var(--mc-text) !important;
            background: #ffffff !important;
          }

          .stChatInput textarea::placeholder {
            color: #94a3b8 !important;
          }

          .stChatInput {
            border: 1px solid #dbe3ee !important;
            border-radius: var(--mc-radius) !important;
          }

          .stChatInputContainer {
            background: #ffffff !important;
          }

          div[data-testid="stMetric"] {
            border: 1px solid var(--mc-line);
            border-radius: var(--mc-radius);
            padding: .8rem;
            background: #ffffff;
          }

          div[data-testid="stMetricValue"] {
            color: var(--mc-ink);
          }

          .stAlert {
            border-radius: var(--mc-radius);
          }

          @media (max-width: 900px) {
            .mc-page-header {
              display: block;
            }

            .mc-header-actions {
              justify-content: flex-start;
              margin-top: .75rem;
            }
          }

          @media (max-width: 640px) {
            .block-container {
              padding-left: .75rem;
              padding-right: .75rem;
            }

            .mc-auth-panel,
            .mc-page-header,
            .mc-card {
              padding: .9rem;
            }

            .mc-auth-title,
            .mc-page-header h1,
            h1 {
              font-size: 1.55rem !important;
            }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def reset_workspace_state() -> None:
    for key in (
        "conversation_id",
        "messages",
        "last_tool_results",
        "last_citations",
        "memory_items",
    ):
        if key in st.session_state:
            del st.session_state[key]


def save_auth(data: dict) -> None:
    previous_user = st.session_state.get("current_user") or {}
    next_user = data["user"]
    if previous_user.get("id") != next_user.get("id"):
        reset_workspace_state()
    st.session_state.access_token = data["access_token"]
    st.session_state.current_user = next_user


def clear_auth() -> None:
    reset_workspace_state()
    st.session_state.access_token = ""
    st.session_state.current_user = None


def auth_headers() -> dict[str, str]:
    token = st.session_state.get("access_token", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


def current_user() -> dict | None:
    return st.session_state.get("current_user")


def require_login() -> dict:
    init_auth_state()
    user = current_user()
    if not st.session_state.access_token or user is None:
        st.info("Log in first to use Maintainers Copilot.")
        st.switch_page("pages/login.py")
        st.stop()
    return user


def require_admin() -> dict:
    user = require_login()
    if user.get("role") != "admin":
        st.error("Admin role required.")
        st.stop()
    return user


def render_user_sidebar() -> None:
    user = current_user()
    if not user:
        return
    st.sidebar.markdown("### Maintainers Copilot")
    st.sidebar.caption("Signed in")
    st.sidebar.markdown(f"**{user['email']}**")
    st.sidebar.caption(f"Role: {user['role']}")
    if st.sidebar.button("Log out"):
        clear_auth()
        st.rerun()


def parse_sse_lines(lines: Iterable[str]) -> Iterator[tuple[str, dict]]:
    event = "message"
    data_lines: list[str] = []
    for raw_line in lines:
        line = raw_line.rstrip("\r")
        if not line:
            if data_lines:
                yield event, json.loads("\n".join(data_lines))
            event = "message"
            data_lines = []
            continue
        if line.startswith("event:"):
            event = line.removeprefix("event:").strip()
        elif line.startswith("data:"):
            data_lines.append(line.removeprefix("data:").strip())
    if data_lines:
        yield event, json.loads("\n".join(data_lines))


def post_json(path: str, *, json_payload: dict, headers: dict | None = None) -> dict:
    response = httpx.post(
        f"{API_BASE_URL}{path}",
        json=json_payload,
        headers=headers or {},
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()
