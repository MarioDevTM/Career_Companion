import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import AppConfig, format_dt_in_tz
from src.models import Document
from src.services.document_service import DocumentService
from src.ui.helpers import get_active_timezone


def render_documents_view(session: Session) -> None:
    tz_name = get_active_timezone(session)
    st.title("Documents & Version Repository")
    st.caption(
        f"Attach CVs, cover letters, study notes, and reference documents ({', '.join(sorted(AppConfig.SUPPORTED_DOC_EXTENSIONS))}). "
        "Files are stored with safe generated filenames, and text extraction reports scanned/unreadable files transparently."
    )

    with st.expander("📤 Upload New Document or Version", expanded=True):
        with st.form("upload_document_form"):
            c1, c2, c3 = st.columns([2, 1, 1])
            title = c1.text_input("Document Title *", placeholder="e.g., Backend Python CV")
            doc_type = c2.selectbox("Document Type", ["CV", "Cover Letter", "Study Note", "Reference Document"])
            version_label = c3.text_input("Version Label", value="v1.0", placeholder="v1.0, 2026-Q4")
            uploaded_file = st.file_uploader(
                "Select File (.txt, .md, .pdf, .docx)",
                type=["txt", "md", "pdf", "docx"],
            )
            if st.form_submit_button("Upload & Extract Text", type="primary"):
                if not uploaded_file:
                    st.error("Please choose a file to upload.")
                else:
                    try:
                        doc = DocumentService.validate_and_store_upload(
                            session=session,
                            file_bytes=uploaded_file.getvalue(),
                            original_filename=uploaded_file.name,
                            title=title or uploaded_file.name,
                            doc_type=doc_type,
                            version_label=version_label,
                        )
                        if doc.extraction_status == "success":
                            st.success(f"Uploaded '{doc.title} ({doc.version_label})' and extracted text successfully!")
                        else:
                            st.warning(
                                f"Uploaded '{doc.title}', but text extraction reported `{doc.extraction_status}`: {doc.extraction_warning}"
                            )
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Upload failed: {exc}")

    docs = list(session.scalars(select(Document).order_by(Document.created_at.desc())).all())
    if not docs:
        st.info("No documents uploaded yet.")
        return

    for doc in docs:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            c1.subheader(f"{doc.title} — `{doc.version_label}` [{doc.doc_type}]")
            c1.caption(
                f"Original file: `{doc.original_filename}` | Safe stored name: `{doc.stored_filename}` | "
                f"Size: {doc.file_size_bytes / 1024:.1f} KB | Uploaded: {format_dt_in_tz(doc.created_at, tz_name)}"
            )
            if doc.extraction_status == "success":
                c1.success("Text extraction: Ready for AI tasks (page metadata preserved)")
            else:
                c1.warning(f"Text extraction status `{doc.extraction_status}`: {doc.extraction_warning}")

            if doc.extracted_text:
                with st.expander("Preview Extracted Text & Page Markers"):
                    st.text(doc.extracted_text[:4000] + ("\n... [Preview Truncated]" if len(doc.extracted_text) > 4000 else ""))

            if c2.button("🗑️ Delete", key=f"del_doc_{doc.id}"):
                DocumentService.delete_document(session, doc.id)
                st.rerun()