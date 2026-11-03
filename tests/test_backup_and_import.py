import io
import json
import zipfile
import pytest

from src.models import UserSetting, JobApplication
from src.schemas import ApplicationInputSchema
from src.services.application_service import ApplicationService
from src.services.backup_service import BackupService


def test_backup_excludes_secrets_and_restores_cleanly(db_session):
    db_session.add(UserSetting(key="timezone", value="Europe/Bucharest"))
    db_session.add(UserSetting(key="firecrawl_api_key", value="SUPER_SECRET_KEY_SHOULD_NOT_EXPORT"))
    db_session.commit()

    ApplicationService.create_application(
        db_session,
        ApplicationInputSchema(company="Original Co", role="Platform Engineer", status="Applied"),
    )

    zip_bytes = BackupService.create_backup_zip_bytes(db_session)
    assert b"SUPER_SECRET_KEY_SHOULD_NOT_EXPORT" not in zip_bytes

    ok, preview, err = BackupService.validate_and_preview_backup(zip_bytes)
    assert ok is True
    assert err is None
    assert preview["table_counts"]["job_applications"] == 1

    # Mutate database, then restore
    ApplicationService.create_application(
        db_session,
        ApplicationInputSchema(company="Temporary Co", role="Temp Role", status="Saved"),
    )
    assert len(ApplicationService.list_applications(db_session)) == 2

    BackupService.restore_from_backup_zip(db_session, zip_bytes, confirm_overwrite=True)
    apps_after = ApplicationService.list_applications(db_session)
    assert len(apps_after) == 1
    assert apps_after[0].company == "Original Co"


def test_failed_restore_rolls_back_and_preserves_existing_data(db_session):
    ApplicationService.create_application(
        db_session,
        ApplicationInputSchema(company="Safe Existing Co", role="Data Engineer", status="Interview"),
    )

    # Create a corrupt manifest with invalid foreign key / column data mid-restore
    corrupt_manifest = {
        "app": "Career Companion",
        "schema_version": "0001_initial_schema",
        "tables": {
            "job_applications": [
                {"id": "not_an_integer", "company": None, "role": None}
            ]
        },
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("backup_manifest.json", json.dumps(corrupt_manifest))

    with pytest.raises(Exception):
        BackupService.restore_from_backup_zip(db_session, buf.getvalue(), confirm_overwrite=True)

    # Verify original data survived intact
    surviving_apps = ApplicationService.list_applications(db_session)
    assert len(surviving_apps) == 1
    assert surviving_apps[0].company == "Safe Existing Co"