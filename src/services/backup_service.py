import csv
import io
import json
import zipfile
from datetime import datetime, date
from typing import Dict, Any, Tuple, Optional
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from src.config import UPLOADS_DIR, utc_now
from src.services.document_service import DocumentService
from src.models import (
    Base,
    DocumentContent,
    UserSetting,
    ProfileEntry,
    Document,
    JobApplication,
    ApplicationStatusEvent,
    ApplicationContact,
    InterviewRecord,
    InterviewQuestionItem,
    Skill,
    ApplicationSkillLink,
    LearningGoal,
    StudyResource,
    StudySession,
    NoteItem,
    TaskItem,
    QuizQuestion,
    QuizAttempt,
    RevisionItem,
    ChatSession,
    ChatMessage,
    learning_goal_applications,
)


SENSITIVE_SETTING_KEYS = {"firecrawl_api_key", "gemini_api_key", "ollama_api_key", "api_key", "secret", "token", "password", "database_url"}

def _sensitive(key: str) -> bool:
    return key.lower() in SENSITIVE_SETTING_KEYS or any(
        part in key.lower() for part in ("secret", "password", "token", "api_key")
    )


SERIALIZATION_MODELS = [
    ("user_settings", UserSetting),
    ("profile_entries", ProfileEntry),
    ("documents", Document),
    ("job_applications", JobApplication),
    ("application_status_events", ApplicationStatusEvent),
    ("application_contacts", ApplicationContact),
    ("interviews", InterviewRecord),
    ("interview_question_items", InterviewQuestionItem),
    ("skills", Skill),
    ("application_skill_links", ApplicationSkillLink),
    ("learning_goals", LearningGoal),
    ("study_resources", StudyResource),
    ("study_sessions", StudySession),
    ("notes", NoteItem),
    ("tasks", TaskItem),
    ("quiz_questions", QuizQuestion),
    ("quiz_attempts", QuizAttempt),
    ("revision_items", RevisionItem),
    ("chat_sessions", ChatSession),
    ("chat_messages", ChatMessage),
]


def _serialize_value(val: Any) -> Any:
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, date):
        return val.isoformat()
    return val


class BackupService:
    @staticmethod
    def export_applications_csv(session: Session) -> str:
        apps = list(session.scalars(select(JobApplication).order_by(JobApplication.id.asc())).all())
        output = io.StringIO()
        fieldnames = [
            "id",
            "company",
            "role",
            "location",
            "work_arrangement",
            "employment_type",
            "status",
            "priority",
            "date_applied",
            "salary_min",
            "salary_max",
            "currency",
            "pay_period",
            "tax_designation",
            "job_url",
            "source",
            "recruiter_name",
            "recruiter_contact",
            "next_action",
            "next_action_due",
            "is_archived",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for app in apps:
            writer.writerow({k: _serialize_value(getattr(app, k)) for k in fieldnames})
        return output.getvalue()

    @staticmethod
    def create_backup_zip_bytes(session: Session) -> bytes:
        """
        Exports all structured database tables and uploaded attachment files into a ZIP archive.
        Never exports API keys or secrets.
        """
        tables_payload: Dict[str, list] = {}
        for table_key, model_cls in SERIALIZATION_MODELS:
            rows = list(session.scalars(select(model_cls)).all())
            serialized_rows = []
            for row in rows:
                if model_cls is UserSetting and _sensitive(row.key):
                    continue
                row_dict = {
                    col.name: _serialize_value(getattr(row, col.name))
                    for col in model_cls.__table__.columns
                }
                serialized_rows.append(row_dict)
            tables_payload[table_key] = serialized_rows

        assoc_rows = session.execute(select(learning_goal_applications)).mappings().all()
        tables_payload["learning_goal_applications"] = [dict(r) for r in assoc_rows]

        manifest = {
            "app": "Career Companion",
            "schema_version": "0001_initial_schema",
            "exported_at": utc_now().isoformat(),
            "tables": tables_payload,
        }

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("backup_manifest.json", json.dumps(manifest, indent=2))
            for doc_row in tables_payload.get("documents", []):
                stored_name = doc_row.get("stored_filename")
                if stored_name:
                    doc = session.get(Document, doc_row["id"])
                    try:
                        content = DocumentService.read_bytes(session, doc)
                    except FileNotFoundError as exc:
                        raise ValueError("A legacy attachment is missing. Restore the uploads folder before exporting.") from exc
                    zf.writestr(f"uploads/{stored_name}", content)

        return buffer.getvalue()

    @staticmethod
    def validate_and_preview_backup(zip_bytes: bytes) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        """
        Validates a backup ZIP archive and returns a summary preview before any changes are committed.
        """
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes), mode="r") as zf:
                names = zf.namelist()
                if len(names) != len(set(names)):
                    return False, {}, "Backup contains duplicate archive entries."
                if sum(item.file_size for item in zf.infolist()) > 250 * 1024 * 1024:
                    return False, {}, "Backup expands beyond the 250 MB restore limit."
                if zf.getinfo("backup_manifest.json").file_size > 50 * 1024 * 1024:
                    return False, {}, "Backup manifest exceeds 50 MB."
                if "backup_manifest.json" not in names:
                    return False, {}, "Archive is missing 'backup_manifest.json'."

                manifest = json.loads(zf.read("backup_manifest.json").decode("utf-8"))
                if manifest.get("app") != "Career Companion" or "tables" not in manifest:
                    return False, {}, "Invalid manifest metadata or missing 'tables' structure."

                tables = manifest["tables"]
                if not isinstance(tables, dict):
                    return False, {}, "'tables' in manifest must be a JSON object."

                counts = {k: len(v) for k, v in tables.items() if isinstance(v, list)}
                attachment_files = [n for n in names if n.startswith("uploads/") and not n.endswith("/")]

                preview = {
                    "exported_at": manifest.get("exported_at"),
                    "schema_version": manifest.get("schema_version"),
                    "table_counts": counts,
                    "attachment_count": len(attachment_files),
                }
                return True, preview, None
        except (zipfile.BadZipFile, json.JSONDecodeError, KeyError, UnicodeDecodeError) as exc:
            return False, {}, f"Backup validation failed: {type(exc).__name__}: {exc}"

    @staticmethod
    def restore_from_backup_zip(
        session: Session, zip_bytes: bytes, confirm_overwrite: bool = False
    ) -> Dict[str, int]:
        """
        Atomically restores structured records and attachments inside a single transaction.
        If any step fails, rolls back the database transaction so existing data is never destroyed.
        """
        if not confirm_overwrite:
            raise ValueError("Explicit overwrite confirmation is required before restoring a backup.")

        is_valid, preview, err_msg = BackupService.validate_and_preview_backup(zip_bytes)
        if not is_valid:
            raise ValueError(err_msg or "Invalid backup archive.")

        with zipfile.ZipFile(io.BytesIO(zip_bytes), mode="r") as zf:
            manifest = json.loads(zf.read("backup_manifest.json").decode("utf-8"))
            tables = manifest["tables"]

            try:
                session.flush()
                session.expunge_all()
                session.execute(DocumentContent.__table__.delete())
                session.execute(learning_goal_applications.delete())
                for _, model_cls in reversed(SERIALIZATION_MODELS):
                    session.execute(model_cls.__table__.delete())

                for table_key, model_cls in SERIALIZATION_MODELS:
                    rows = tables.get(table_key, [])
                    for row_data in rows:
                        if model_cls is UserSetting and _sensitive(str(row_data.get("key", ""))):
                            continue
                        coerced = BackupService._coerce_row_types(model_cls, row_data)
                        session.add(model_cls(**coerced))
                    session.flush()

                for assoc in tables.get("learning_goal_applications", []):
                    session.execute(learning_goal_applications.insert().values(**assoc))

                for row in tables.get("documents", []):
                    filename = row["stored_filename"]
                    if not filename or any(x in filename for x in ("/", "\\", "..")):
                        raise ValueError("Invalid attachment name in backup.")
                    archive_name = f"uploads/{filename}"
                    if archive_name not in zf.namelist():
                        raise ValueError("Backup is missing an original attachment; restore cancelled.")
                    session.add(DocumentContent(document_id=row["id"], content=zf.read(archive_name)))

                # Explicit restored IDs do not advance PostgreSQL SERIAL sequences.
                if session.bind.dialect.name == "postgresql":
                    for table in Base.metadata.sorted_tables:
                        if "id" in table.c and table.c.id.type.python_type is int:
                            session.execute(text(
                                f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), "
                                f"COALESCE((SELECT MAX(id) FROM {table.name}), 1), "
                                f"EXISTS(SELECT 1 FROM {table.name}))"
                            ))
                session.commit()
                return preview.get("table_counts", {})
            except Exception:
                session.rollback()
                raise

    @staticmethod
    def _coerce_row_types(model_cls: Any, row_data: Dict[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for col in model_cls.__table__.columns:
            val = row_data.get(col.name)
            if val is None:
                result[col.name] = None
                continue
            py_type = col.type.python_type
            if py_type is datetime and isinstance(val, str):
                result[col.name] = datetime.fromisoformat(val)
            elif py_type is date and isinstance(val, str):
                result[col.name] = date.fromisoformat(val)
            else:
                result[col.name] = val
        return result
