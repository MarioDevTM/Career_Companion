from datetime import date, datetime, timezone
import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.config import AppConfig, format_dt_in_tz
from src.models import (
    JobApplication,
    InterviewRecord,
    TaskItem,
    RevisionItem,
    ApplicationStatusEvent,
    StudySession,
)
from src.services.demo_service import DemoService
from src.ui.helpers import get_active_timezone, render_status_badge, navigate_to


def render_dashboard_view(session: Session) -> None:
    tz_name = get_active_timezone(session)
    today = date.today()
    now_utc = datetime.now(timezone.utc)

    st.title("Career Companion Dashboard")
    st.caption(
        "Save a job → identify requirements → choose preparation goals → study & practice → record interview outcomes → adjust future preparation."
    )

    # Quick Actions Bar
    qa_col1, qa_col2, qa_col3, qa_col4 = st.columns(4)
    if qa_col1.button("➕ Add Application", use_container_width=True, type="primary"):
        navigate_to("Applications", open_new_app_form=True)
    if qa_col2.button("🗓️ Log Interview", use_container_width=True):
        navigate_to("Interviews")
    if qa_col3.button("⏱️ Start Study Session", use_container_width=True):
        navigate_to("Learning", learning_tab="Study & Sessions")
    if qa_col4.button("✨ Open AI Assistant", use_container_width=True):
        navigate_to("AI Assistant")

    all_apps = list(
        session.scalars(
            select(JobApplication).where(JobApplication.is_archived.is_(False))
        ).all()
    )

    if not all_apps:
        st.info(
            "Your workspace has no job applications yet. Use **Add Application** above to add your first role, "
            "or load fictional sample data below to explore the full workflow."
        )
        if st.button("Load Fictional Demo Data"):
            DemoService.load_fictional_demo_data(session)
            st.success("Loaded fictional demo data!")
            st.rerun()

    active_apps = [a for a in all_apps if a.status in AppConfig.ACTIVE_STATUSES]
    interviews = list(
        session.scalars(
            select(InterviewRecord)
            .options(selectinload(InterviewRecord.application))
            .order_by(InterviewRecord.scheduled_at.asc())
        ).all()
    )
    upcoming_interviews = [
        i
        for i in interviews
        if (i.scheduled_at.replace(tzinfo=timezone.utc) if i.scheduled_at.tzinfo is None else i.scheduled_at)
        >= now_utc
    ]

    followups_due = [
        a for a in active_apps if a.next_action_due is not None and a.next_action_due <= today
    ]
    tasks_due_today = list(
        session.scalars(
            select(TaskItem).where(
                TaskItem.status != "Done",
                TaskItem.due_date.is_not(None),
                TaskItem.due_date <= today,
            )
        ).all()
    )
    revisions_due = list(
        session.scalars(
            select(RevisionItem).where(RevisionItem.next_review_date <= today)
        ).all()
    )

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Active Applications", len(active_apps))
    m2.metric("Upcoming Interviews", len(upcoming_interviews))
    m3.metric("Follow-ups Due/Overdue", len(followups_due))
    m4.metric("Tasks Due Today/Overdue", len(tasks_due_today))
    m5.metric("Revisions Due", len(revisions_due))

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Active Applications & Follow-ups")
        if not active_apps:
            st.caption("No active applications currently tracked.")
        else:
            for app in active_apps[:6]:
                badge = render_status_badge(app.status)
                due_str = ""
                if app.next_action_due:
                    overdue_tag = "⚠️ OVERDUE" if app.next_action_due < today else "📅 Due"
                    due_str = f" — **{overdue_tag} ({app.next_action_due})**: {app.next_action or 'Follow up'}"
                st.markdown(
                    f"**{app.company}** — {app.role} {badge}{due_str}",
                    unsafe_allow_html=True,
                )

        st.subheader("Upcoming Interviews")
        if not upcoming_interviews:
            st.caption("No upcoming interviews scheduled.")
        else:
            for iv in upcoming_interviews[:5]:
                dt_label = format_dt_in_tz(iv.scheduled_at, tz_name)
                st.markdown(
                    f"- **{iv.application.company}** ({iv.stage}, {iv.format}) — `{dt_label}`"
                )

    with col_right:
        st.subheader("Study Tasks & Revisions Due Today")
        if not tasks_due_today and not revisions_due:
            st.caption("All caught up on today's tasks and spaced-revision flashcards!")
        else:
            for t in tasks_due_today[:5]:
                st.markdown(f"- **[Task - {t.task_type}]** {t.title} (Due: `{t.due_date}`)")
            for rev in revisions_due[:5]:
                st.markdown(
                    f"- **[Revision Stage {rev.stage_index + 1}]** {rev.prompt_front[:80]} (Due: `{rev.next_review_date}`)"
                )

        st.subheader("Recent Activity")
        recent_events = list(
            session.scalars(
                select(ApplicationStatusEvent)
                .options(selectinload(ApplicationStatusEvent.application))
                .order_by(ApplicationStatusEvent.changed_at.desc())
                .limit(5)
            ).all()
        )
        recent_sessions = list(
            session.scalars(
                select(StudySession).order_by(StudySession.logged_at.desc()).limit(5)
            ).all()
        )
        if not recent_events and not recent_sessions:
            st.caption("No recent status changes or study sessions logged yet.")
        else:
            for ev in recent_events:
                app_label = f"{ev.application.company} ({ev.application.role})" if ev.application else f"App #{ev.application_id}"
                st.markdown(
                    f"- 🔄 **{app_label}** → `{ev.new_status}` ({format_dt_in_tz(ev.changed_at, tz_name)})"
                )
            for ss in recent_sessions:
                st.markdown(
                    f"- 📚 **Study Session**: {ss.duration_minutes} min ({ss.activity_type}) — `{format_dt_in_tz(ss.logged_at, tz_name)}`"
                )