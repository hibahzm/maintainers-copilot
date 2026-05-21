import httpx
import streamlit as st

from ui import API_BASE_URL, clear_auth, current_user, init_auth_state, save_auth

init_auth_state()

user = current_user()

st.markdown(
    """
    <section class="mc-auth-panel">
      <div class="mc-auth-brand">
        <span class="mc-mark">MC</span>
        <div>
          <strong>Maintainers Copilot</strong><br />
          <span class="mc-caption">Internal maintainer workspace</span>
        </div>
      </div>
      <h1 class="mc-auth-title">Sign in before you triage.</h1>
      <p class="mc-auth-copy">
        The Streamlit app is the authenticated console for maintainers and admins.
        It contains the full chat, retrieval evidence, memory inspection, and widget controls.
      </p>
      <div class="mc-surface-grid">
        <div class="mc-surface">
          <strong>Internal chat</strong>
          <span>Authenticated chat with tool evidence, citations, and memory controls.</span>
        </div>
        <div class="mc-surface">
          <strong>Public widget</strong>
          <span>React surface that host apps embed; no admin tools or memory writes.</span>
        </div>
        <div class="mc-surface">
          <strong>Shared backend</strong>
          <span>Both surfaces call the same FastAPI chat and retrieval services.</span>
        </div>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)
st.write("")

with st.container(border=True):
    if user:
        st.success(f"Signed in as {user['email']} ({user['role']})")
        if st.button("Log out", type="primary", use_container_width=True):
            clear_auth()
            st.rerun()
        st.stop()

    st.subheader("Account")
    st.markdown(
        """
        <div class="mc-auth-helper">
          Local admin account: <strong>admin@maintainers.local</strong> /
          <strong>admin-password</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    login_tab, register_tab = st.tabs(["Login", "Register"])

    with login_tab:
        email = st.text_input("Email", value="admin@maintainers.local", key="login_email")
        password = st.text_input(
            "Password",
            value="admin-password",
            type="password",
            key="login_password",
        )

        if st.button("Login", type="primary", use_container_width=True):
            try:
                response = httpx.post(
                    f"{API_BASE_URL}/auth/login",
                    json={"email": email, "password": password},
                    timeout=20.0,
                )
                response.raise_for_status()
                save_auth(response.json())
                st.rerun()
            except httpx.HTTPStatusError as exc:
                detail = exc.response.json().get("detail", exc.response.text)
                st.error(f"Auth failed: {detail}")
            except httpx.HTTPError as exc:
                st.error(f"Auth request failed: {exc}")

    with register_tab:
        register_email = st.text_input("Email", key="register_email")
        register_password = st.text_input(
            "Password",
            type="password",
            key="register_password",
        )

        if st.button("Create account", type="primary", use_container_width=True):
            try:
                response = httpx.post(
                    f"{API_BASE_URL}/auth/register",
                    json={"email": register_email, "password": register_password},
                    timeout=20.0,
                )
                response.raise_for_status()
                save_auth(response.json())
                st.rerun()
            except httpx.HTTPStatusError as exc:
                detail = exc.response.json().get("detail", exc.response.text)
                st.error(f"Registration failed: {detail}")
            except httpx.HTTPError as exc:
                st.error(f"Registration request failed: {exc}")
