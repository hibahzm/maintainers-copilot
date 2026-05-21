import httpx
import streamlit as st

from ui import API_BASE_URL, clear_auth, current_user, init_auth_state, save_auth

init_auth_state()

user = current_user()

left, right = st.columns([1.08, 0.92], gap="large")

with left:
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
              <strong>8501</strong>
              <span>Private workspace. Login is required.</span>
            </div>
            <div class="mc-surface">
              <strong>4173</strong>
              <span>Public React widget bundle used inside host apps.</span>
            </div>
            <div class="mc-surface">
              <strong>8080</strong>
              <span>Demo host page that embeds the widget.</span>
            </div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

with right:
    with st.container(border=True):
        if user:
            st.success(f"Signed in as {user['email']} ({user['role']})")
            if st.button("Log out", type="primary", use_container_width=True):
                clear_auth()
                st.rerun()
            st.stop()

        st.subheader("Account")
        st.caption("Local admin: admin@maintainers.local / admin-password")
        mode = st.segmented_control("Action", ["Login", "Register"], default="Login")
        email = st.text_input("Email", value="admin@maintainers.local" if mode == "Login" else "")
        password = st.text_input(
            "Password",
            value="admin-password" if mode == "Login" else "",
            type="password",
        )

        if st.button(mode, type="primary", use_container_width=True):
            endpoint = "/auth/login" if mode == "Login" else "/auth/register"
            try:
                response = httpx.post(
                    f"{API_BASE_URL}{endpoint}",
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
