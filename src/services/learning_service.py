import json
from datetime import date, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload

from src.config import utc_now
from src.models import (
    Skill,
    LearningGoal,
    JobApplication,
    StudyResource,
    StudySession,
    NoteItem,
    QuizQuestion,
    QuizAttempt,
    RevisionItem,
)

# Documented 6-stage spaced-revision interval ladder in days
REVISION_STAGE_INTERVALS = [1, 3, 7, 14, 30, 60]


class LearningService:
    @staticmethod
    def create_or_update_skill(
        session: Session, name: str, category: str = "General", self_confidence: int = 2
    ) -> Skill:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Skill name cannot be empty.")
        confidence = max(1, min(5, int(self_confidence)))
        skill = session.scalar(select(Skill).where(Skill.name.ilike(cleaned)))
        if skill:
            skill.category = category
            skill.self_confidence = confidence
        else:
            skill = Skill(name=cleaned, category=category, self_confidence=confidence)
            session.add(skill)
        session.commit()
        session.refresh(skill)
        return skill

    @staticmethod
    def get_skill_metrics(session: Session, skill_id: int) -> Dict[str, Any]:
        """
        Separates self-reported confidence from empirical practice performance.
        Never labels a skill as 'Proficient / Mastered' merely from reading a note or completing one quiz.
        Requires >= 3 quiz attempts with >= 80% accuracy AND >= 60 minutes of logged study sessions.
        """
        skill = session.get(Skill, skill_id)
        if not skill:
            raise ValueError("Skill not found.")

        attempts = list(
            session.scalars(select(QuizAttempt).where(QuizAttempt.skill_id == skill_id)).all()
        )
        attempt_count = len(attempts)
        correct_count = sum(1 for a in attempts if a.is_correct)
        accuracy_pct = round((correct_count / attempt_count) * 100.0, 1) if attempt_count > 0 else None

        total_minutes = (
            session.scalar(
                select(func.coalesce(func.sum(StudySession.duration_minutes), 0)).where(
                    StudySession.skill_id == skill_id
                )
            )
            or 0
        )

        if attempt_count == 0 and total_minutes == 0:
            evidence_status = "Untested"
        elif attempt_count < 3 or total_minutes < 60:
            evidence_status = "In Practice (Insufficient Evidence for Mastery)"
        elif accuracy_pct is not None and accuracy_pct >= 80.0:
            evidence_status = "Demonstrated Proficiency"
        else:
            evidence_status = "Needs Reinforcement"

        return {
            "skill_id": skill.id,
            "name": skill.name,
            "category": skill.category,
            "self_confidence": skill.self_confidence,
            "quiz_attempts": attempt_count,
            "quiz_accuracy_pct": accuracy_pct,
            "study_minutes": int(total_minutes),
            "evidence_status": evidence_status,
        }

    @staticmethod
    def create_learning_goal(
        session: Session,
        title: str,
        goal_type: str = "Job Preparation",
        description: Optional[str] = None,
        target_date: Optional[date] = None,
        application_ids: Optional[List[int]] = None,
    ) -> LearningGoal:
        goal = LearningGoal(
            title=title.strip(),
            goal_type=goal_type,
            description=description,
            target_date=target_date,
            status="Active",
        )
        if application_ids:
            apps = list(
                session.scalars(select(JobApplication).where(JobApplication.id.in_(application_ids))).all()
            )
            goal.applications = apps
        session.add(goal)
        session.commit()
        session.refresh(goal)
        return goal

    @staticmethod
    def list_learning_goals(session: Session) -> List[LearningGoal]:
        stmt = (
            select(LearningGoal)
            .options(selectinload(LearningGoal.applications), selectinload(LearningGoal.resources))
            .order_by(LearningGoal.created_at.desc())
        )
        return list(session.scalars(stmt).all())

    @staticmethod
    def log_study_session(
        session: Session,
        duration_minutes: int,
        activity_type: str,
        notes: Optional[str] = None,
        learning_goal_id: Optional[int] = None,
        skill_id: Optional[int] = None,
    ) -> StudySession:
        if duration_minutes <= 0:
            raise ValueError("Study duration must be greater than zero minutes.")
        entry = StudySession(
            learning_goal_id=learning_goal_id,
            skill_id=skill_id,
            duration_minutes=duration_minutes,
            activity_type=activity_type,
            notes=notes,
        )
        session.add(entry)
        session.commit()
        return entry

    @staticmethod
    def create_quiz_question(
        session: Session,
        question_text: str,
        options: List[str],
        correct_option_index: int,
        explanation: str,
        skill_id: Optional[int] = None,
        learning_goal_id: Optional[int] = None,
        source_citation: Optional[str] = None,
        suggested_revisit_topic: Optional[str] = None,
    ) -> QuizQuestion:
        q = QuizQuestion(
            skill_id=skill_id,
            learning_goal_id=learning_goal_id,
            question_text=question_text,
            options_json=json.dumps(options),
            correct_option_index=correct_option_index,
            explanation=explanation,
            source_citation=source_citation,
            suggested_revisit_topic=suggested_revisit_topic,
        )
        session.add(q)
        session.commit()
        session.refresh(q)
        return q

    @staticmethod
    def record_quiz_attempt(
        session: Session, quiz_question_id: int, selected_option_index: int
    ) -> QuizAttempt:
        question = session.get(QuizQuestion, quiz_question_id)
        if not question:
            raise ValueError("Quiz question not found.")
        is_correct = int(selected_option_index) == int(question.correct_option_index)
        attempt = QuizAttempt(
            quiz_question_id=quiz_question_id,
            skill_id=question.skill_id,
            selected_option_index=selected_option_index,
            is_correct=is_correct,
        )
        session.add(attempt)
        session.commit()
        session.refresh(attempt)
        return attempt

    @staticmethod
    def create_revision_item(
        session: Session,
        prompt_front: str,
        answer_back: str,
        skill_id: Optional[int] = None,
        learning_goal_id: Optional[int] = None,
        initial_review_date: Optional[date] = None,
    ) -> RevisionItem:
        item = RevisionItem(
            skill_id=skill_id,
            learning_goal_id=learning_goal_id,
            prompt_front=prompt_front.strip(),
            answer_back=answer_back.strip(),
            stage_index=0,
            interval_days=REVISION_STAGE_INTERVALS[0],
            next_review_date=initial_review_date or (date.today() + timedelta(days=1)),
        )
        session.add(item)
        session.commit()
        return item

    @staticmethod
    def record_revision_review(
        session: Session, revision_id: int, recall_quality: str, today: Optional[date] = None
    ) -> RevisionItem:
        """
        Updates the revision item according to the documented 6-stage ladder [1, 3, 7, 14, 30, 60] days:
        - 'Hard': resets stage_index to 0 (1 day)
        - 'Good': increments stage_index by 1
        - 'Easy': increments stage_index by 2
        """
        item = session.get(RevisionItem, revision_id)
        if not item:
            raise ValueError("Revision item not found.")

        ref_date = today or date.today()
        max_stage = len(REVISION_STAGE_INTERVALS) - 1

        if recall_quality == "Hard":
            new_stage = 0
        elif recall_quality == "Easy":
            new_stage = min(max_stage, item.stage_index + 2)
        else:  # Good
            new_stage = min(max_stage, item.stage_index + 1)

        interval = REVISION_STAGE_INTERVALS[new_stage]
        item.stage_index = new_stage
        item.interval_days = interval
        item.next_review_date = ref_date + timedelta(days=interval)
        item.last_reviewed_at = utc_now()
        item.review_count += 1
        session.commit()
        return item

    @staticmethod
    def reschedule_revision_item(
        session: Session, revision_id: int, new_review_date: date
    ) -> RevisionItem:
        item = session.get(RevisionItem, revision_id)
        if not item:
            raise ValueError("Revision item not found.")
        item.next_review_date = new_review_date
        session.commit()
        return item

    @staticmethod
    def save_note(
        session: Session,
        title: str,
        content: str,
        origin: str = "User Note",
        application_id: Optional[int] = None,
        learning_goal_id: Optional[int] = None,
        skill_id: Optional[int] = None,
    ) -> NoteItem:
        note = NoteItem(
            title=title.strip(),
            content=content.strip(),
            origin=origin,
            application_id=application_id,
            learning_goal_id=learning_goal_id,
            skill_id=skill_id,
        )
        session.add(note)
        session.commit()
        return note