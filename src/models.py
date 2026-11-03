from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import (
    String,
    LargeBinary,
    Integer,
    Float,
    Boolean,
    Text,
    Date,
    DateTime,
    ForeignKey,
    Table,
    Column,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from src.config import utc_now


class Base(DeclarativeBase):
    pass


learning_goal_applications = Table(
    "learning_goal_applications",
    Base.metadata,
    Column("learning_goal_id", Integer, ForeignKey("learning_goals.id", ondelete="CASCADE"), primary_key=True),
    Column("application_id", Integer, ForeignKey("job_applications.id", ondelete="CASCADE"), primary_key=True),
)


class UserSetting(Base):
    __tablename__ = "user_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class ProfileEntry(Base):
    __tablename__ = "profile_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # Project, Technical Skill, Experience, STAR Story
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    organization: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    role_or_skill: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    date_range: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    situation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    task: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    competency_tags: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)  # CV, Cover Letter, Study Note, Reference
    version_label: Mapped[str] = mapped_column(String(50), default="v1.0", nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    file_extension: Mapped[str] = mapped_column(String(20), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    page_map_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list of {"page": n, "text": "..."}
    extraction_status: Mapped[str] = mapped_column(String(50), default="success")  # success, empty_or_scanned, failed
    extraction_warning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class JobApplication(Base):
    __tablename__ = "job_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    work_arrangement: Mapped[str] = mapped_column(String(50), default="Unspecified")
    employment_type: Mapped[str] = mapped_column(String(50), default="Full-time")
    job_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    job_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    date_applied: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Saved", nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="Medium", nullable=False)

    salary_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    salary_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), default="EUR")
    pay_period: Mapped[Optional[str]] = mapped_column(String(30), default="Monthly")
    tax_designation: Mapped[Optional[str]] = mapped_column(String(20), default="Unspecified")

    recruiter_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    recruiter_contact: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    next_action: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    next_action_due: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    cv_document_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    cover_letter_document_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )

    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    cv_document: Mapped[Optional["Document"]] = relationship("Document", foreign_keys=[cv_document_id])
    cover_letter_document: Mapped[Optional["Document"]] = relationship(
        "Document", foreign_keys=[cover_letter_document_id]
    )
    status_events: Mapped[List["ApplicationStatusEvent"]] = relationship(
        "ApplicationStatusEvent", back_populates="application", cascade="all, delete-orphan"
    )
    contacts: Mapped[List["ApplicationContact"]] = relationship(
        "ApplicationContact", back_populates="application", cascade="all, delete-orphan"
    )
    interviews: Mapped[List["InterviewRecord"]] = relationship(
        "InterviewRecord", back_populates="application", cascade="all, delete-orphan"
    )
    tasks: Mapped[List["TaskItem"]] = relationship(
        "TaskItem", back_populates="application", cascade="all, delete-orphan"
    )
    skill_links: Mapped[List["ApplicationSkillLink"]] = relationship(
        "ApplicationSkillLink", back_populates="application", cascade="all, delete-orphan"
    )
    learning_goals: Mapped[List["LearningGoal"]] = relationship(
        "LearningGoal", secondary=learning_goal_applications, back_populates="applications"
    )


class ApplicationStatusEvent(Base):
    __tablename__ = "application_status_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=False
    )
    old_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    application: Mapped["JobApplication"] = relationship("JobApplication", back_populates="status_events")


class ApplicationContact(Base):
    __tablename__ = "application_contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    contact_info: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    application: Mapped["JobApplication"] = relationship("JobApplication", back_populates="contacts")


class InterviewRecord(Base):
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=False
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    format: Mapped[str] = mapped_column(String(100), default="Video Call")
    stage: Mapped[str] = mapped_column(String(100), default="Technical Round")
    participants: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    prep_checklist_json: Mapped[Optional[str]] = mapped_column(Text, default="[]")
    questions_to_ask: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reflection: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    follow_up_actions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    application: Mapped["JobApplication"] = relationship("JobApplication", back_populates="interviews")
    question_items: Mapped[List["InterviewQuestionItem"]] = relationship(
        "InterviewQuestionItem", back_populates="interview", cascade="all, delete-orphan"
    )


class InterviewQuestionItem(Base):
    __tablename__ = "interview_question_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interview_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(50), default="Technical")  # Technical, Behavioral, General
    origin: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # ai_practice, user_practice, confirmed_asked
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    interview: Mapped["InterviewRecord"] = relationship("InterviewRecord", back_populates="question_items")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(100), default="General")
    self_confidence: Mapped[int] = mapped_column(Integer, default=1)  # 1 to 5
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    application_links: Mapped[List["ApplicationSkillLink"]] = relationship(
        "ApplicationSkillLink", back_populates="skill", cascade="all, delete-orphan"
    )


class ApplicationSkillLink(Base):
    __tablename__ = "application_skill_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=False
    )
    skill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    requirement_level: Mapped[str] = mapped_column(String(30), default="Required")  # Required, Preferred
    source_type: Mapped[str] = mapped_column(String(30), default="Explicit")  # Explicit, Inferred
    evidence_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    application: Mapped["JobApplication"] = relationship("JobApplication", back_populates="skill_links")
    skill: Mapped["Skill"] = relationship("Skill", back_populates="application_links")


class LearningGoal(Base):
    __tablename__ = "learning_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    goal_type: Mapped[str] = mapped_column(String(50), default="Job Preparation")  # Job Preparation, Certification, General Skill
    target_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Active")  # Active, Completed, On hold
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    applications: Mapped[List["JobApplication"]] = relationship(
        "JobApplication", secondary=learning_goal_applications, back_populates="learning_goals"
    )
    resources: Mapped[List["StudyResource"]] = relationship(
        "StudyResource", back_populates="learning_goal", cascade="all, delete-orphan"
    )


class StudyResource(Base):
    __tablename__ = "study_resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    learning_goal_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("learning_goals.id", ondelete="CASCADE"), nullable=True
    )
    skill_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    learning_goal: Mapped[Optional["LearningGoal"]] = relationship("LearningGoal", back_populates="resources")


class StudySession(Base):
    __tablename__ = "study_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    learning_goal_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("learning_goals.id", ondelete="SET NULL"), nullable=True
    )
    skill_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    activity_type: Mapped[str] = mapped_column(String(50), default="Reading / Practice")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class NoteItem(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    origin: Mapped[str] = mapped_column(String(50), default="User Note")  # User Note, AI Saved Output
    application_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("job_applications.id", ondelete="SET NULL"), nullable=True
    )
    learning_goal_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("learning_goals.id", ondelete="SET NULL"), nullable=True
    )
    skill_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TaskItem(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    task_type: Mapped[str] = mapped_column(String(50), default="General")  # Application, Interview Prep, Study
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="Todo")  # Todo, In Progress, Done
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    origin: Mapped[str] = mapped_column(String(50), default="User")  # User, AI Proposal
    application_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=True
    )
    learning_goal_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("learning_goals.id", ondelete="SET NULL"), nullable=True
    )
    skill_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    application: Mapped[Optional["JobApplication"]] = relationship("JobApplication", back_populates="tasks")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )
    learning_goal_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("learning_goals.id", ondelete="SET NULL"), nullable=True
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    options_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON list of 4 options
    correct_option_index: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    source_citation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    suggested_revisit_topic: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quiz_question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False
    )
    skill_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )
    selected_option_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RevisionItem(Base):
    __tablename__ = "revision_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )
    learning_goal_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("learning_goals.id", ondelete="SET NULL"), nullable=True
    )
    prompt_front: Mapped[str] = mapped_column(Text, nullable=False)
    answer_back: Mapped[str] = mapped_column(Text, nullable=False)
    stage_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0..5 -> [1, 3, 7, 14, 30, 60] days
    interval_days: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    next_review_date: Mapped[date] = mapped_column(Date, nullable=False)
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    mode: Mapped[str] = mapped_column(String(50), nullable=False)
    application_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("job_applications.id", ondelete="SET NULL"), nullable=True
    )
    learning_goal_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("learning_goals.id", ondelete="SET NULL"), nullable=True
    )
    skill_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )
    selected_doc_ids_json: Mapped[Optional[str]] = mapped_column(Text, default="[]")
    selected_note_ids_json: Mapped[Optional[str]] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    structured_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    was_context_truncated: Mapped[bool] = mapped_column(Boolean, default=False)
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")


class DocumentContent(Base):
    """Original attachment bytes stored transactionally with the workspace database."""
    __tablename__ = "document_contents"
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
