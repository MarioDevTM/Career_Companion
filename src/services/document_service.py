import io
import json
import uuid
from pathlib import Path
from typing import Tuple, List, Dict, Optional
from pypdf import PdfReader
import docx
from sqlalchemy.orm import Session

from src.config import AppConfig, UPLOADS_DIR
from src.models import Document


class DocumentService:
    @staticmethod
    def validate_and_store_upload(
        session: Session,
        file_bytes: bytes,
        original_filename: str,
        title: str,
        doc_type: str,
        version_label: str = "v1.0",
    ) -> Document:
        if not file_bytes:
            raise ValueError("Uploaded file is empty.")

        max_bytes = AppConfig.get_max_upload_bytes()
        if len(file_bytes) > max_bytes:
            raise ValueError(
                f"File size ({len(file_bytes) // (1024 * 1024)} MB) exceeds maximum limit of {max_bytes // (1024 * 1024)} MB."
            )

        ext = Path(original_filename).suffix.lower()
        if ext not in AppConfig.SUPPORTED_DOC_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type '{ext}'. Supported types: {', '.join(sorted(AppConfig.SUPPORTED_DOC_EXTENSIONS))}"
            )

        safe_stored_name = f"{uuid.uuid4().hex}{ext}"
        target_path = UPLOADS_DIR / safe_stored_name
        target_path.write_bytes(file_bytes)

        extracted_text, page_map, status, warning = DocumentService.extract_text_and_pages(
            file_bytes, ext
        )

        doc = Document(
            title=title.strip() or original_filename,
            doc_type=doc_type,
            version_label=version_label.strip() or "v1.0",
            original_filename=original_filename,
            stored_filename=safe_stored_name,
            file_extension=ext,
            file_size_bytes=len(file_bytes),
            extracted_text=extracted_text,
            page_map_json=json.dumps(page_map),
            extraction_status=status,
            extraction_warning=warning,
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)
        return doc

    @staticmethod
    def extract_text_and_pages(
        file_bytes: bytes, extension: str
    ) -> Tuple[str, List[Dict[str, object]], str, Optional[str]]:
        """
        Extracts text and page/section metadata.
        Reports unreadable or scanned documents clearly without pretending empty extraction succeeded.
        """
        ext = extension.lower()
        try:
            if ext in {".txt", ".md"}:
                text = file_bytes.decode("utf-8", errors="replace").strip()
                if not text:
                    return "", [], "empty_or_scanned", "The text file contains no readable characters."
                return text, [{"page": 1, "text": text}], "success", None

            if ext == ".pdf":
                reader = PdfReader(io.BytesIO(file_bytes))
                pages_data: List[Dict[str, object]] = []
                combined_parts: List[str] = []
                for idx, page in enumerate(reader.pages, start=1):
                    page_text = (page.extract_text() or "").strip()
                    if page_text:
                        pages_data.append({"page": idx, "text": page_text})
                        combined_parts.append(f"[Page {idx}]\n{page_text}")

                full_text = "\n\n".join(combined_parts).strip()
                if not full_text:
                    return (
                        "",
                        [],
                        "empty_or_scanned",
                        "No selectable text could be extracted from this PDF. It appears to be a scanned image or empty PDF.",
                    )
                return full_text, pages_data, "success", None

            if ext == ".docx":
                document = docx.Document(io.BytesIO(file_bytes))
                paragraphs = [p.text.strip() for p in document.paragraphs if p.text and p.text.strip()]
                full_text = "\n\n".join(paragraphs).strip()
                if not full_text:
                    return (
                        "",
                        [],
                        "empty_or_scanned",
                        "No readable paragraph text was found in this DOCX file.",
                    )
                return full_text, [{"page": 1, "text": full_text}], "success", None

            return "", [], "failed", f"Unsupported extension: {ext}"
        except Exception as exc:
            return (
                "",
                [],
                "failed",
                f"Document text extraction failed: {type(exc).__name__}: {exc}",
            )

    @staticmethod
    def format_document_for_context(doc: Document) -> str:
        if doc.extraction_status != "success" or not doc.extracted_text:
            return (
                f"=== DOCUMENT: {doc.title} ({doc.original_filename}, Version {doc.version_label}) ===\n"
                f"[UNREADABLE DOCUMENT WARNING: {doc.extraction_warning or 'No extractable text available.'}]"
            )
        return (
            f"=== DOCUMENT: {doc.title} ({doc.original_filename}, Version {doc.version_label}) ===\n"
            f"{doc.extracted_text}"
        )

    @staticmethod
    def delete_document(session: Session, document_id: int) -> None:
        doc = session.get(Document, document_id)
        if not doc:
            return
        file_path = UPLOADS_DIR / doc.stored_filename
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError:
                pass
        session.delete(doc)
        session.commit()