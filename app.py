import streamlit as st

from src.database import init_db, get_db_session
from src.access import require_owner, validate_storage
from src.config import AppConfig
from src.ui.helpers import (
    get_active_timezone,
    get_active_ollama_model,
    get_active_ollama_base_url,
)
from src.ui.dashboard_view import render_dashboard_view
from src.ui.applications_view import render_applications_view
from src.ui.interviews_view import render_interviews_view
from src.ui.learning_view import render_learning_view
from src.ui.assistant_view import render_assistant_view
from src.ui.experience_view import render_experience_view
from src.ui.documents_view import render_documents_view
from src.ui.insights_view import render_insights_view
from src.ui.settings_view import render_settings_view


NAVIGATION_PAGES = [
    "Dashboard",
    "Applications",
    "Interviews",
    "Learning",
    "AI Assistant",
    "Experience Bank",
    "Documents",
    "Insights",
    "Settings",
]


@st.cache_resource(show_spinner=False)
def initialize_database(database_url: str) -> None:
    # Avoid repeating schema inspection/migrations on every widget rerun.
    init_db(database_url)


def main() -> None:
    st.set_page_config(
        page_title="Career Companion",
        page_icon=":material/work:",
        layout="wide",
        initial_sidebar_state="auto",
    )

    require_owner()
    validate_storage()
    try:
        initialize_database(AppConfig.get_database_url())
    except Exception:
        st.error("Could not open the workspace database. Check the deployment DATABASE_URL, SSL settings, and database availability.")
        st.stop()

    pending_page = st.session_state.pop("_navigate_to", None)
    if pending_page in NAVIGATION_PAGES:
        st.session_state["nav_page"] = pending_page

    if "nav_page" not in st.session_state:
        st.session_state["nav_page"] = "Dashboard"

    with get_db_session() as session:
        active_tz = get_active_timezone(session)
        active_model = get_active_ollama_model(session)
        active_base_url = get_active_ollama_base_url(session)

        with st.sidebar:
            st.title("Career Companion")
            st.caption("Personal Job Search & Learning Hub")
            selected_page = st.radio(
                "Navigation",
                NAVIGATION_PAGES,
                index=NAVIGATION_PAGES.index(st.session_state["nav_page"])
                if st.session_state["nav_page"] in NAVIGATION_PAGES
                else 0,
                key="nav_page",
            )

            st.divider()
            st.caption("**AI Provider:** `Ollama`")
            st.caption(f"**Model:** `{active_model}`")

            st.caption(f"**Timezone:** `{active_tz}`")

        if selected_page == "Dashboard":
            render_dashboard_view(session)
        elif selected_page == "Applications":
            render_applications_view(session)
        elif selected_page == "Interviews":
            render_interviews_view(session)
        elif selected_page == "Learning":
            render_learning_view(session)
        elif selected_page == "AI Assistant":
            render_assistant_view(session)
        elif selected_page == "Experience Bank":
            render_experience_view(session)
        elif selected_page == "Documents":
            render_documents_view(session)
        elif selected_page == "Insights":
            render_insights_view(session)
        elif selected_page == "Settings":
            render_settings_view(session)


if __name__ == "__main__":
    main()
