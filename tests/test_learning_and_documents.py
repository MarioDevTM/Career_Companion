from datetime import date, timedelta
from src.services.learning_service import LearningService
from src.services.document_service import DocumentService


def test_skill_mastery_requires_sufficient_practice_and_study(db_session):
    skill = LearningService.create_or_update_skill(db_session, "Distributed Caching", "Backend", self_confidence=5)

    # Reading or completing a single quiz must NOT mark the skill as proficient/mastered
    q = LearningService.create_quiz_question(
        db_session,
        question_text="What is cache stampede?",
        options=["Thundering herd on expiry", "Network partition", "Disk full", "DNS loop"],
        correct_option_index=0,
        explanation="Concurrent recomputation when a popular key expires.",
        skill_id=skill.id,
    )
    LearningService.record_quiz_attempt(db_session, q.id, 0)
    m1 = LearningService.get_skill_metrics(db_session, skill.id)
    assert m1["evidence_status"] == "In Practice (Insufficient Evidence for Mastery)"

    # After >= 3 attempts at >= 80% accuracy AND >= 60 study minutes, proficiency is demonstrated
    LearningService.record_quiz_attempt(db_session, q.id, 0)
    LearningService.record_quiz_attempt(db_session, q.id, 0)
    LearningService.log_study_session(db_session, 65, "Hands-on Coding", skill_id=skill.id)

    m2 = LearningService.get_skill_metrics(db_session, skill.id)
    assert m2["evidence_status"] == "Demonstrated Proficiency"


def test_revision_schedule_progression_and_reschedule(db_session):
    today = date(2026, 11, 3)
    rev = LearningService.create_revision_item(
        db_session, "Prompt", "Answer", initial_review_date=today
    )
    assert rev.stage_index == 0

    # 'Easy' advances 2 stages -> index 2 (7 days)
    LearningService.record_revision_review(db_session, rev.id, "Easy", today=today)
    assert rev.stage_index == 2
    assert rev.interval_days == 7
    assert rev.next_review_date == today + timedelta(days=7)

    # 'Hard' resets to stage 0 (1 day)
    LearningService.record_revision_review(db_session, rev.id, "Hard", today=today)
    assert rev.stage_index == 0
    assert rev.interval_days == 1

    # Manual reschedule
    custom_date = today + timedelta(days=10)
    LearningService.reschedule_revision_item(db_session, rev.id, custom_date)
    assert rev.next_review_date == custom_date


def test_document_upload_and_empty_extraction_reporting(db_session):
    doc_ok = DocumentService.validate_and_store_upload(
        db_session,
        file_bytes=b"# Python Study Notes\nUnderstand generators and coroutines.",
        original_filename="notes.md",
        title="Python Notes",
        doc_type="Study Note",
    )
    assert doc_ok.extraction_status == "success"
    assert doc_ok.stored_filename != "notes.md"

    # Whitespace-only text reports empty_or_scanned clearly
    doc_empty = DocumentService.validate_and_store_upload(
        db_session,
        file_bytes=b"   \n  ",
        original_filename="blank.txt",
        title="Blank Doc",
        doc_type="Reference Document",
    )
    assert doc_empty.extraction_status == "empty_or_scanned"
    assert doc_empty.extraction_warning is not None