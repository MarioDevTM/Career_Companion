from zoneinfo import available_timezones
import streamlit as st
from sqlalchemy.orm import Session

from src.config import AppConfig
from src.database import set_setting
from src.services.ollama_service import OllamaService
from src.services.backup_service import BackupService
from src.services.demo_service import DemoService
from src.ui.helpers import (
    get_active_timezone,
    get_active_ollama_model,
    get_active_ollama_base_url,
)


COMMON_TIMEZONES = [
    "Europe/Bucharest",
    "UTC",
    "Europe/London",
    "Europe/Berlin",
    "America/New_York",
    "America/Los_Angeles",
    "Asia/Tokyo",
]


def render_settings_view(session: Session) -> None:
    st.title("Settings, Portability & Backups")

    current_tz = get_active_timezone(session)
    current_model = get_active_ollama_model(session)
    current_base_url = get_active_ollama_base_url(session)
    ollama = OllamaService(base_url=current_base_url, model_name=current_model)

    col_ai, col_tz = st.columns(2)

    with col_ai:
        st.subheader("Local Ollama AI Configuration")
        st.caption("No external LLM API key is required. Inference runs locally via Ollama.")

        if AppConfig.get_firecrawl_api_key():
            st.info("🌐 Optional Firecrawl Web Search: `FIRECRAWL_API_KEY` is configured.")
        else:
            st.caption("🌐 Optional Firecrawl Web Search: Not configured (local materials work without it).")

        with st.form("ollama_settings_form"):
            new_base_url = st.text_input(
                "Ollama Base URL (`OLLAMA_BASE_URL`)",
                value=current_base_url,
                help="Default: http://localhost:11434",
            )
            new_model = st.text_input(
                "Configured Ollama Model (`OLLAMA_MODEL`)",
                value=current_model,
                help="Default: qwen2.5:0.5b (pull via: ollama pull qwen2.5:0.5b)",
            )
            if st.form_submit_button("Save Ollama Settings"):
                if new_base_url.strip() and new_model.strip():
                    set_setting(session, "ollama_base_url", new_base_url.strip().rstrip("/"))
                    set_setting(session, "ollama_model", new_model.strip())
                    st.success(
                        f"Updated Ollama settings to model `{new_model.strip()}` at `{new_base_url.strip().rstrip('/')}`"
                    )
                    st.rerun()

        if st.button("🔌 Run Live Ollama & Model Check"):
            with st.spinner(f"Checking Ollama at `{current_base_url}` and testing `{current_model}`..."):
                res = ollama.check_connection()
            if res.success:
                st.success(
                    f"✅ Local Ollama connection verified! Model `{res.model_used}` responded: `{res.text}`"
                )
            else:
                st.error(f"Connection check failed (`{res.error_type}`): {res.error_message}")
                if res.error_type == "service_unavailable":
                    st.code("ollama serve", language="bash")
                elif res.error_type == "model_not_found":
                    st.code(f"ollama pull {current_model}", language="bash")

    with col_tz:
        st.subheader("Timezone Preferences")
        all_tzs = sorted(available_timezones())
        tz_choices = COMMON_TIMEZONES + [t for t in all_tzs if t not in COMMON_TIMEZONES]
        with st.form("tz_settings_form"):
            selected_tz = st.selectbox(
                "Display Timezone (defaults to Europe/Bucharest)",
                tz_choices,
                index=tz_choices.index(current_tz) if current_tz in tz_choices else 0,
            )
            if st.form_submit_button("Save Timezone"):
                set_setting(session, "timezone", selected_tz)
                st.success(f"Display timezone updated to `{selected_tz}`.")
                st.rerun()

    st.divider()
    st.subheader("Portability, Exports & Full Backups")
    st.caption("Secrets and API keys are strictly excluded from all CSV exports and backup archives.")

    exp_col1, exp_col2, exp_col3 = st.columns(3)
    csv_data = BackupService.export_applications_csv(session)
    exp_col1.download_button(
        "📄 Download Applications CSV",
        data=csv_data,
        file_name="career_companion_applications.csv",
        mime="text/csv",
        use_container_width=True,
    )

    zip_bytes = BackupService.create_backup_zip_bytes(session)
    exp_col2.download_button(
        "📦 Download Full Backup (.zip)",
        data=zip_bytes,
        file_name="career_companion_backup.zip",
        mime="application/zip",
        use_container_width=True,
    )

    if exp_col3.button("🎭 Load Fictional Demo Data", use_container_width=True):
        DemoService.load_fictional_demo_data(session)
        st.success("Fictional demo data added!")
        st.rerun()

    st.divider()
    st.subheader("Validate & Restore from Backup (.zip)")
    st.info(
        "Uploading a backup runs validation and shows a non-destructive preview first. "
        "Existing data is never overwritten without your explicit confirmation, and restore failures roll back cleanly."
    )

    restore_file = st.file_uploader("Upload Career Companion Backup (.zip)", type=["zip"])
    if restore_file is not None:
        raw_zip = restore_file.getvalue()
        is_valid, preview, err = BackupService.validate_and_preview_backup(raw_zip)
        if not is_valid:
            st.error(f"❌ Invalid backup file: {err}")
        else:
            st.success(
                f"✅ Backup validated! Exported at `{preview.get('exported_at')}` "
                f"(Schema `{preview.get('schema_version')}`, Attachments: `{preview.get('attachment_count')}`)."
            )
            st.json(preview.get("table_counts", {}))
            confirm_restore = st.checkbox(
                "⚠️ I understand that restoring this backup will replace current workspace records."
            )
            if st.button("Restore Workspace from Backup", type="primary", disabled=not confirm_restore):
                try:
                    restored_counts = BackupService.restore_from_backup_zip(
                        session, raw_zip, confirm_overwrite=True
                    )
                    st.success(f"Workspace restored successfully! Restored tables: {restored_counts}")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Restore failed and existing data was preserved via rollback: {exc}")