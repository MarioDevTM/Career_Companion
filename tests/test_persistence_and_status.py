from datetime import date
import pytest
from pydantic import ValidationError

from src.schemas import ApplicationInputSchema
from src.services.application_service import ApplicationService
from src.services.insights_service import InsightsService


def test_application_persistence_and_status_history_without_duplication(db_session):
    payload = ApplicationInputSchema(
        company="Acme Robotics",
        role="Backend Engineer",
        status="Saved",
        priority="High",
        salary_min=3000,
        salary_max=4000,
    )
    app = ApplicationService.create_application(db_session, payload)
    assert app.id is not None
    assert len(app.status_events) == 1
    assert app.status_events[0].new_status == "Saved"

    # Editing non-status fields does not duplicate the application or add spurious status events
    updated_payload = ApplicationInputSchema(
        company="Acme Robotics",
        role="Senior Backend Engineer",
        status="Saved",
        priority="High",
        salary_min=3500,
        salary_max=4500,
    )
    ApplicationService.update_application(db_session, app.id, updated_payload)
    apps = ApplicationService.list_applications(db_session)
    assert len(apps) == 1
    assert apps[0].role == "Senior Backend Engineer"
    assert len(apps[0].status_events) == 1

    # Updating status appends a timestamped status event
    applied_payload = ApplicationInputSchema(
        company="Acme Robotics",
        role="Senior Backend Engineer",
        status="Applied",
        date_applied=date.today(),
    )
    ApplicationService.update_application(db_session, app.id, applied_payload, status_note="Submitted online")
    interview_payload = ApplicationInputSchema(
        company="Acme Robotics",
        role="Senior Backend Engineer",
        status="Interview",
        date_applied=date.today(),
    )
    ApplicationService.update_application(db_session, app.id, interview_payload, status_note="Phone screen passed")
    rejected_payload = ApplicationInputSchema(
        company="Acme Robotics",
        role="Senior Backend Engineer",
        status="Rejected",
        date_applied=date.today(),
    )
    ApplicationService.update_application(db_session, app.id, rejected_payload, status_note="Final round rejection")

    refreshed = ApplicationService.list_applications(db_session)[0]
    statuses_recorded = [ev.new_status for ev in refreshed.status_events]
    assert statuses_recorded == ["Saved", "Applied", "Interview", "Rejected"]

    # Verify insights exclude Saved-only roles and recognize historical Interview progression
    ApplicationService.create_application(
        db_session,
        ApplicationInputSchema(company="Saved Only Co", role="Python Dev", status="Saved"),
    )
    metrics = InsightsService.compute_application_metrics(db_session)
    assert metrics["total_records"] == 2
    assert metrics["saved_unapplied_count"] == 1
    assert metrics["submitted_applications_denominator"] == 1
    assert metrics["ever_interviewed_count"] == 1
    assert metrics["interview_conversion_pct"] == 100.0


def test_salary_bounds_validation():
    with pytest.raises(ValidationError):
        ApplicationInputSchema(
            company="Invalid Corp",
            role="Engineer",
            salary_min=6000,
            salary_max=4000,
        )