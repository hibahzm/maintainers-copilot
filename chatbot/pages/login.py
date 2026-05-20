import os

import httpx
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

st.title("Login")
st.caption("Register or log in to enable authenticated memory and admin features.")

if "access_token" not in st.session_state:
    st.session_state.access_token = ""
if "current_user" not in st.session_state:
    st.session_state.current_user = None


def save_auth(data: dict) -> None:
    st.session_state.access_token = data["access_token"]
    st.session_state.current_user = data["user"]


if st.session_state.current_user:
    user = st.session_state.current_user
    st.success(f"Signed in as {user['email']} ({user['role']})")
    if st.button("Log out"):
        st.session_state.access_token = ""
        st.session_state.current_user = None
        st.rerun()
    st.stop()

mode = st.radio("Choose action", ["Login", "Register"], horizontal=True)
email = st.text_input("Email")
password = st.text_input("Password", type="password")

if st.button(mode, type="primary"):
    endpoint = "/auth/login" if mode == "Login" else "/auth/register"
    try:
        response = httpx.post(
            f"{API_BASE_URL}{endpoint}",
            json={"email": email, "password": password},
            timeout=20.0,
        )
        response.raise_for_status()
        save_auth(response.json())
        st.success("Signed in.")
        st.rerun()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.json().get("detail", exc.response.text)
        st.error(f"Auth failed: {detail}")
    except httpx.HTTPError as exc:
        st.error(f"Auth request failed: {exc}")
