import streamlit as st

from ui import inject_app_styles, init_auth_state

st.set_page_config(page_title="Maintainers Copilot", layout="wide")
inject_app_styles()
init_auth_state()

if st.session_state.current_user:
    pages = {
        "Workspace": [
            st.Page("pages/chat.py", title="Chat"),
            st.Page("pages/memory_inspector.py", title="Memory"),
        ],
        "Account": [
            st.Page("pages/login.py", title="Account"),
        ],
    }
    if st.session_state.current_user.get("role") == "admin":
        pages["Admin"] = [
            st.Page("pages/widget_config.py", title="Widget"),
        ]
else:
    pages = [st.Page("pages/login.py", title="Login")]

selected_page = st.navigation(pages)
selected_page.run()
