"""One private owner workspace; authentication runs before any data is loaded."""
import streamlit as st
from src.config import AppConfig, setting, is_cloud


def owner_allowed(claims, owner_email: str) -> bool:
    return bool(owner_email and claims.get("email_verified") is True
                and str(claims.get("email", "")).casefold() == owner_email.casefold())


def require_owner() -> None:
    if not is_cloud() and setting("AUTH_REQUIRED", "false").lower() != "true":
        return
    owner = setting("OWNER_EMAIL").strip()
    if not owner:
        st.error("Private workspace is locked. Configure OWNER_EMAIL and OIDC authentication in deployment secrets.")
        st.stop()
    if not st.user.is_logged_in:
        st.title("Career Companion")
        st.caption("Your private job search and learning workspace")
        if st.button("Sign in", type="primary"):
            st.login()
        st.stop()
    if not owner_allowed(st.user, owner):
        st.error("This account does not have access to this workspace.")
        if st.button("Sign out"):
            st.logout()
        st.stop()
    if st.sidebar.button("Sign out", key="owner_logout"):
        st.session_state.clear()
        st.logout()


def validate_storage() -> None:
    if is_cloud() and not AppConfig.get_database_url().startswith("postgresql"):
        st.error("Cloud mode requires a persistent PostgreSQL DATABASE_URL. Local SQLite storage is not durable on Community Cloud.")
        st.stop()
