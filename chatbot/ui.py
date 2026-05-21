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
            --mc-bg: #f4f7fb;
            --mc-ink: #0b1220;
            --mc-panel: #ffffff;
            --mc-panel-soft: #f8fafc;
            --mc-text: #111827;
            --mc-muted: #64748b;
            --mc-line: #d8e0ea;
            --mc-line-strong: #b8c4d3;
            --mc-accent: #16a34a;
            --mc-accent-strong: #15803d;
            --mc-info: #0f766e;
            --mc-warning: #b45309;
            --mc-danger: #be123c;
            --mc-radius: 8px;
          }

          .stApp {
            background: var(--mc-bg);
            color: var(--mc-text);
          }

          .block-container {
            max-width: 1280px;
            padding-top: 1.25rem;
            padding-bottom: 2rem;
          }

          [data-testid="stSidebar"] {
            background: #0b1220;
            border-right: 1px solid rgba(255, 255, 255, 0.08);
          }

          [data-testid="stSidebar"] * {
            color: #e5edf7 !important;
          }

          [data-testid="stSidebar"] div[role="separator"] {
            border-color: rgba(226, 232, 240, 0.14);
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
            align-items: flex-start;
            justify-content: space-between;
            gap: 1rem;
            border: 1px solid var(--mc-line);
            border-radius: var(--mc-radius);
            padding: 1.1rem 1.2rem;
            background: var(--mc-panel);
            box-shadow: 0 12px 34px rgba(15, 23, 42, 0.06);
          }

          .mc-page-header h1 {
            margin: 0 0 .35rem;
            font-size: 2rem !important;
            line-height: 1.1 !important;
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
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.05);
          }

          .mc-card h3 {
            margin: 0 0 .4rem;
            font-size: 1rem;
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
            padding: 1.35rem;
            background: var(--mc-panel);
            box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
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
            background: #0b1220;
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

          .mc-surface-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
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
            border: 1px solid #bbf7d0;
            border-radius: 999px;
            padding: .25rem .65rem;
            background: #f0fdf4;
            color: #166534 !important;
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
            grid-template-columns: repeat(3, minmax(0, 1fr));
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

          div.stButton > button:hover,
          div.stDownloadButton > button:hover {
            border-color: var(--mc-accent);
            color: var(--mc-accent-strong);
          }

          div.stButton > button[kind="primary"] {
            background: var(--mc-accent);
            color: #ffffff;
            border-color: var(--mc-accent);
          }

          div.stButton > button[kind="primary"]:hover {
            background: var(--mc-accent-strong);
            color: #ffffff;
            border-color: var(--mc-accent-strong);
          }

          [data-testid="stChatMessage"] {
            border: 1px solid var(--mc-line);
            border-radius: var(--mc-radius);
            background: #ffffff;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.05);
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
            .mc-auth-shell,
            .mc-surface-grid,
            .mc-port-grid {
              grid-template-columns: 1fr;
            }

            .mc-page-header {
              display: block;
            }

            .mc-header-actions {
              justify-content: flex-start;
              margin-top: .75rem;
            }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def save_auth(data: dict) -> None:
    st.session_state.access_token = data["access_token"]
    st.session_state.current_user = data["user"]


def clear_auth() -> None:
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
        st.warning("Log in first to use Maintainers Copilot.")
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
