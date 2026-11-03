import json
from datetime import datetime, date
from typing import List, Optional, Tuple
from sqlalchemy import select, or_
from sqlalchemy.orm import Session, selectinload

from src.config import utc_now
from src.models import (
    JobApplication,
    ApplicationStatusEvent,
    ApplicationContact,
    InterviewRecord,
    InterviewQuestionItem,
    TaskItem,
    Skill,
    ApplicationSkillLink,
)
from src.schemas import ApplicationInputSchema


class ApplicationService:
    @staticmethod
    def find_potential_duplicates(
        session: Session,
        company: str,
        role: str,
        job_url: Optional[str] = None,
        exclude_id: Optional[int] = None,
    ) -> List[JobApplication]:
        conditions = [
            (JobApplication.company.ilike(company.strip())) & (JobApplication.role.ilike(role.strip()))
        ]
        if job_url and job_url.strip():
            conditions.append(JobApplication.job_url == job_url.strip())

        stmt = select(JobApplication).where(or_(*conditions))
        if exclude_id is not None:
            stmt = stmt.where(JobApplication.id != exclude_id)
        return list(session.scalars(stmt).all())

    @staticmethod
    def create_application(
        session: Session, payload: ApplicationInputSchema, status_note: Optional[str] = None
    ) -> JobApplication:
        app = JobApplication(**payload.model_dump())
        session.add(app)
        session.flush()

        event = ApplicationStatusEvent(
            application_id=app.id,
            old_status=None,
            new_status=app.status,
            changed_at=utc_now(),
            note=status_note or "Initial creation",
        )
        session.add(event)
        session.commit()
        session.refresh(app)
        return app

    @staticmethod
    def update_application(
        session: Session,
        application_id: int,
        payload: ApplicationInputSchema,
        status_note: Optional[str] = None,
    ) -> JobApplication:
        app = session.get(JobApplication, application_id)
        if not app:
            raise ValueError(f"Application {application_id} not found.")

        old_status = app.status
        data = payload.model_dump()
        for key, value in data.items():
            setattr(app, key, value)
        app.updated_at = utc_now()

        if old_status != app.status:
            event = ApplicationStatusEvent(
                application_id=app.id,
                old_status=old_status,
                new_status=app.status,
                changed_at=utc_now(),
                note=status_note or f"Status changed from {old_status} to {app.status}",
            )
            session.add(event)

        session.commit()
        session.refresh(app)
        return app

    @staticmethod
    def list_applications(
        session: Session,
        search_query: Optional[str] = None,
        statuses: Optional[List[str]] = None,
        priority: Optional[str] = None,
        include_archived: bool = False,
    ) -> List[JobApplication]:
        stmt = (
            select(JobApplication)
            .options(
                selectinload(JobApplication.status_events),
                selectinload(JobApplication.interviews),
                selectinload(JobApplication.tasks),
                selectinload(JobApplication.skill_links).selectinload(ApplicationSkillLink.skill),
                selectinload(JobApplication.cv_document),
                selectinload(JobApplication.cover_letter_document),
            )
            .order_by(JobApplication.updated_at.desc())
        )
        if not include_archived:
            stmt = stmt.where(JobApplication.is_archived.is_(False))
        if statuses:
            stmt = stmt.where(JobApplication.status.in_(statuses))
        if priority and priority != "All":
            stmt = stmt.where(JobApplication.priority == priority)
        if search_query and search_query.strip():
            q = f"%{search_query.strip()}%"
            stmt = stmt.where(
                or_(
                    JobApplication.company.ilike(q),
                    JobApplication.role.ilike(q),
                    JobApplication.location.ilike(q),
                    JobApplication.notes.ilike(q),
                )
            )
        return list(session.scalars(stmt).all())

    @staticmethod
    def set_archived(session: Session, application_id: int, archived: bool) -> JobApplication:
        app = session.get(JobApplication, application_id)
        if not app:
            raise ValueError(f"Application {application_id} not found.")
        app.is_archived = archived
        app.updated_at = utc_now()
        session.commit()
        return app

    @staticmethod
    def delete_application(session: Session, application_id: int) -> None:
        app = session.get(JobApplication, application_id)
        if app:
            session.delete(app)
            session.commit()

    @staticmethod
    def add_contact(
        session: Session,
        application_id: int,
        name: str,
        role: Optional[str] = None,
        contact_info: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> ApplicationContact:
        contact = ApplicationContact(
            application_id=application_id,
            name=name.strip(),
            role=role,
            contact_info=contact_info,
            notes=notes,
        )
        session.add(contact)
        session.commit()
        return contact

    @staticmethod
    def create_interview(
        session: Session,
        application_id: int,
        scheduled_at: datetime,
        format_str: str,
        stage: str,
        participants: Optional[str] = None,
        checklist_items: Optional[List[dict]] = None,
        questions_to_ask: Optional[str] = None,
    ) -> InterviewRecord:
        interview = InterviewRecord(
            application_id=application_id,
            scheduled_at=scheduled_at,
            format=format_str,
            stage=stage,
            participants=participants,
            prep_checklist_json=json.dumps(checklist_items or []),
            questions_to_ask=questions_to_ask,
        )
        session.add(interview)
        session.commit()
        session.refresh(interview)
        return interview

    @staticmethod
    def update_interview_details(
        session: Session,
        interview_id: int,
        checklist_items: List[dict],
        questions_to_ask: Optional[str],
        feedback: Optional[str],
        reflection: Optional[str],
        follow_up_actions: Optional[str],
    ) -> InterviewRecord:
        interview = session.get(InterviewRecord, interview_id)
        if not interview:
            raise ValueError("Interview not found.")
        interview.prep_checklist_json = json.dumps(checklist_items)
        interview.questions_to_ask = questions_to_ask
        interview.feedback = feedback
        interview.reflection = reflection
        interview.follow_up_actions = follow_up_actions
        session.commit()
        return interview

    @staticmethod
    def add_interview_question(
        session: Session,
        interview_id: int,
        category: str,
        origin: str,
        question_text: str,
        answer_notes: Optional[str] = None,
    ) -> InterviewQuestionItem:
        if origin not in {"ai_practice", "user_practice", "confirmed_asked"}:
            raise ValueError(f"Invalid question origin: {origin}")
        item = InterviewQuestionItem(
            interview_id=interview_id,
            category=category,
            origin=origin,
            question_text=question_text.strip(),
            answer_notes=answer_notes,
        )
        session.add(item)
        session.commit()
        return item

    @staticmethod
    def update_interview_question(
        session: Session,
        question_id: int,
        origin: str,
        answer_notes: Optional[str],
    ) -> InterviewQuestionItem:
        item = session.get(InterviewQuestionItem, question_id)
        if not item:
            raise ValueError("Interview question item not found.")
        if origin not in {"ai_practice", "user_practice", "confirmed_asked"}:
            raise ValueError(f"Invalid question origin: {origin}")
        item.origin = origin
        item.answer_notes = answer_notes
        session.commit()
        return item

    @staticmethod
    def link_skill_to_application(
        session: Session,
        application_id: int,
        skill_name: str,
        category: str = "Technical",
        requirement_level: str = "Required",
        source_type: str = "Explicit",
        evidence_snippet: Optional[str] = None,
    ) -> Tuple[Skill, ApplicationSkillLink]:
        cleaned = skill_name.strip()
        skill = session.scalar(select(Skill).where(Skill.name.ilike(cleaned)))
        if not skill:
            skill = Skill(name=cleaned, category=category, self_confidence=2)
            session.add(skill)
            session.flush()

        existing_link = session.scalar(
            select(ApplicationSkillLink).where(
                ApplicationSkillLink.application_id == application_id,
                ApplicationSkillLink.skill_id == skill.id,
            )
        )
        if existing_link:
            existing_link.requirement_level = requirement_level
            existing_link.source_type = source_type
            existing_link.evidence_snippet = evidence_snippet
            session.commit()
            return skill, existing_link

        link = ApplicationSkillLink(
            application_id=application_id,
            skill_id=skill.id,
            requirement_level=requirement_level,
            source_type=source_type,
            evidence_snippet=evidence_snippet,
        )
        session.add(link)
        session.commit()
        return skill, link

    @staticmethod
    def create_task(
        session: Session,
        title: str,
        task_type: str = "General",
        description: Optional[str] = None,
        due_date: Optional[date] = None,
        priority: str = "Medium",
        origin: str = "User",
        application_id: Optional[int] = None,
        learning_goal_id: Optional[int] = None,
        skill_id: Optional[int] = None,
    ) -> TaskItem:
        task = TaskItem(
            title=title.strip(),
            description=description,
            task_type=task_type,
            due_date=due_date,
            priority=priority,
            origin=origin,
            application_id=application_id,
            learning_goal_id=learning_goal_id,
            skill_id=skill_id,
            status="Todo",
        )
        session.add(task)
        session.commit()
        return task

    @staticmethod
    def toggle_task_status(session: Session, task_id: int, new_status: str) -> TaskItem:
        task = session.get(TaskItem, task_id)
        if not task:
            raise ValueError("Task not found.")
        task.status = new_status
        task.completed_at = utc_now() if new_status == "Done" else None
        session.commit()
        return task