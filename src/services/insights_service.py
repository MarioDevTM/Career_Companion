from collections import Counter
from typing import Dict, Any, List
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.models import (
    JobApplication,
    ApplicationSkillLink,
    StudySession,
    QuizAttempt,
    Skill,
)


INTERVIEW_OR_LATER_STATUSES = {"Interview", "Offer", "Accepted"}
EMPLOYER_RESPONSE_STATUSES = {"Screening", "Assessment", "Interview", "Offer", "Accepted", "Rejected"}


class InsightsService:
    @staticmethod
    def compute_application_metrics(session: Session) -> Dict[str, Any]:
        """
        Computes application funnel and conversion rates with explicit denominators:
        - Saved-but-not-applied roles (where status is 'Saved' and status history never left 'Saved')
          are excluded from conversion rate denominators.
        - Uses status history (ApplicationStatusEvent) to determine whether an application ever
          reached an interview or offer stage, even if its final status became 'Rejected' or 'Withdrawn'.
        """
        apps = list(
            session.scalars(
                select(JobApplication).options(
                    selectinload(JobApplication.status_events),
                    selectinload(JobApplication.skill_links).selectinload(ApplicationSkillLink.skill),
                )
            ).all()
        )

        total_records = len(apps)
        saved_only_count = 0
        applied_pool: List[JobApplication] = []

        ever_responded_count = 0
        ever_interviewed_count = 0
        ever_offered_count = 0

        for app in apps:
            historical_statuses = {ev.new_status for ev in app.status_events} | {app.status}
            non_saved_statuses = historical_statuses - {"Saved"}
            if not non_saved_statuses:
                saved_only_count += 1
                continue

            applied_pool.append(app)
            if historical_statuses & EMPLOYER_RESPONSE_STATUSES:
                ever_responded_count += 1
            if historical_statuses & INTERVIEW_OR_LATER_STATUSES:
                ever_interviewed_count += 1
            if historical_statuses & {"Offer", "Accepted"}:
                ever_offered_count += 1

        denom = len(applied_pool)
        response_rate = round((ever_responded_count / denom) * 100.0, 1) if denom > 0 else 0.0
        interview_rate = round((ever_interviewed_count / denom) * 100.0, 1) if denom > 0 else 0.0
        offer_rate = round((ever_offered_count / denom) * 100.0, 1) if denom > 0 else 0.0

        status_counts = Counter(app.status for app in apps)
        source_counts = Counter((app.source or "Unspecified") for app in apps)

        skill_counter: Counter = Counter()
        for app in apps:
            for link in app.skill_links:
                if link.skill:
                    skill_counter[link.skill.name] += 1

        timeline_rows = []
        for app in apps:
            effective_date = app.date_applied or app.created_at.date()
            timeline_rows.append(
                {
                    "date": effective_date,
                    "status": app.status,
                    "company": app.company,
                    "source": app.source or "Unspecified",
                }
            )

        return {
            "total_records": total_records,
            "saved_unapplied_count": saved_only_count,
            "submitted_applications_denominator": denom,
            "ever_responded_count": ever_responded_count,
            "ever_interviewed_count": ever_interviewed_count,
            "ever_offered_count": ever_offered_count,
            "response_rate_pct": response_rate,
            "interview_conversion_pct": interview_rate,
            "offer_conversion_pct": offer_rate,
            "small_sample_warning": denom < 5,
            "status_distribution": dict(status_counts),
            "source_distribution": dict(source_counts),
            "top_requested_skills": skill_counter.most_common(12),
            "timeline_df": pd.DataFrame(timeline_rows) if timeline_rows else pd.DataFrame(),
        }

    @staticmethod
    def compute_learning_metrics(session: Session) -> Dict[str, Any]:
        sessions = list(session.scalars(select(StudySession)).all())
        attempts = list(session.scalars(select(QuizAttempt)).all())
        skills = {s.id: s.name for s in session.scalars(select(Skill)).all()}

        study_rows = [
            {
                "date": s.logged_at.date(),
                "minutes": s.duration_minutes,
                "skill": skills.get(s.skill_id, "General / Unlinked"),
                "activity": s.activity_type,
            }
            for s in sessions
        ]

        skill_quiz_summary: Dict[str, Dict[str, int]] = {}
        for att in attempts:
            s_name = skills.get(att.skill_id, "General")
            bucket = skill_quiz_summary.setdefault(s_name, {"attempts": 0, "correct": 0})
            bucket["attempts"] += 1
            if att.is_correct:
                bucket["correct"] += 1

        quiz_rows = [
            {
                "skill": name,
                "attempts": vals["attempts"],
                "accuracy_pct": round((vals["correct"] / vals["attempts"]) * 100.0, 1),
            }
            for name, vals in skill_quiz_summary.items()
            if vals["attempts"] > 0
        ]

        return {
            "total_study_minutes": sum(s.duration_minutes for s in sessions),
            "total_quiz_attempts": len(attempts),
            "study_df": pd.DataFrame(study_rows) if study_rows else pd.DataFrame(),
            "quiz_df": pd.DataFrame(quiz_rows) if quiz_rows else pd.DataFrame(),
        }
