import streamlit as st
from sqlalchemy.orm import Session

from src.database import get_setting
from src.config import AppConfig, setting, is_cloud
from html import escape


STATUS_COLORS = {
    "Saved": "#64748b",
    "Applied": "#2563eb",
    "Screening": "#0284c7",
    "Assessment": "#7c3aed",
    "Interview": "#d97706",
    "Offer": "#059669",
    "Accepted": "#16a34a",
    "Rejected": "#dc2626",
    "Withdrawn": "#475569",
    "On hold": "#ca8a04",
    "No response": "#94a3b8",
}


def get_active_timezone(session: Session) -> str:
    return get_setting(session, "timezone", AppConfig.get_default_timezone())


def get_active_ollama_model(session: Session) -> str:
    return (AppConfig.get_ollama_model() if setting("OLLAMA_MODEL") or is_cloud()
            else get_setting(session, "ollama_model", AppConfig.get_ollama_model()))


def get_active_ollama_base_url(session: Session) -> str:
    return (AppConfig.get_ollama_base_url() if setting("OLLAMA_BASE_URL") or is_cloud()
            else get_setting(session, "ollama_base_url", AppConfig.get_ollama_base_url()))


def render_status_badge(status: str) -> str:
    color = STATUS_COLORS.get(status, "#475569")
    return (
        f"<span style='background-color:{color}1a; color:{color}; border:1px solid {color}66; "
        f"padding:2px 10px; border-radius:999px; font-size:0.82rem; font-weight:600;'>{escape(status)}</span>"
    )


def render_origin_badge(origin: str) -> str:
    labels = {
        "ai_practice": ("AI-Generated Practice", "#7c3aed"),
        "user_practice": ("User Practice", "#0284c7"),
        "confirmed_asked": ("Confirmed Asked in Interview", "#059669"),
        "User Note": ("User Note", "#0284c7"),
        "AI Saved Output": ("AI Suggestion Saved by User", "#7c3aed"),
        "User": ("Saved User Task", "#0284c7"),
        "AI Proposal": ("Saved from AI Proposal", "#7c3aed"),
    }
    text, color = labels.get(origin, (origin, "#64748b"))
    return (
        f"<span style='background-color:{color}1a; color:{color}; border:1px solid {color}55; "
        f"padding:2px 8px; border-radius:6px; font-size:0.78rem; font-weight:600;'>{escape(text)}</span>"
    )


def navigate_to(page_name: str, **kwargs):
    st.session_state["_navigate_to"] = page_name
    for k, v in kwargs.items():
        st.session_state[k] = v
    st.rerun()
