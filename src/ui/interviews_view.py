import json
from datetime import datetime, date, time as dt_time, timezone
from zoneinfo import ZoneInfo
import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.config import format_dt_in_tz
from src.models import JobApplication, InterviewRecord
from src.services.application_service import ApplicationService
from src.ui.helpers import get_active_timezone, render_origin_badge


def render_interviews_view(session: Session) -> None:
    tz_name = get_active_timezone(session)
    st.title("Interview Workspace")
    st.caption(
        "Manage interview stages, preparation checklists, questions to ask, and preserve the distinction between AI-generated practice questions and questions confirmed asked."
    )

    apps = list(session.scalars(select(JobApplication).order_by(JobApplication.company.asc())).all())
    if not apps:
        st.info("Add a job application first to schedule and prepare for interviews.")
        return

    app_map = {a.id: f"{a.company} — {a.role} ({a.status})" for a in apps}
    default_app_id = st.session_state.get("selected_app_id", apps[0].id)
    app_ids = list(app_map.keys())
    selected_app_id = st.selectbox(
        "Select Application",
        app_ids,
        index=app_ids.index(default_app_id) if default_app_id in app_ids else 0,
        format_func=lambda x: app_map[x],
    )

    with st.expander("➕ Log / Schedule Interview for This Application", expanded=False):
        with st.form("create_interview_form"):
            c1, c2, c3, c4 = st.columns(4)
            iv_date = c1.date_input("Interview Date", value=date.today())
            iv_time = c2.time_input("Interview Time", value=dt_time(10, 0))
            iv_format = c3.selectbox("Format", ["Video Call", "On-site", "Phone Screen", "Live Coding / Take-home"])
            iv_stage = c4.text_input("Stage", value="Technical Round 1")
            participants = st.text_input("Participants / Interviewers")
            checklist_raw = st.text_area(
                "Preparation Checklist (one item per line)",
                placeholder="Review job description\nTest microphone and IDE\nPrepare 2 STAR stories",
            )
            questions_to_ask = st.text_area("Questions I Want to Ask the Interviewers")

            if st.form_submit_button("Save Interview"):
                local_tz = ZoneInfo(tz_name)
                scheduled_local = datetime.combine(iv_date, iv_time).replace(tzinfo=local_tz)
                scheduled_utc = scheduled_local.astimezone(timezone.utc)
                checklist = [
                    {"item": line.strip(), "done": False}
                    for line in checklist_raw.splitlines()
                    if line.strip()
                ]
                ApplicationService.create_interview(
                    session=session,
                    application_id=selected_app_id,
                    scheduled_at=scheduled_utc,
                    format_str=iv_format,
                    stage=iv_stage,
                    participants=participants,
                    checklist_items=checklist,
                    questions_to_ask=questions_to_ask,
                )
                st.success("Interview recorded!")
                st.rerun()

    interviews = list(
        session.scalars(
            select(InterviewRecord)
            .where(InterviewRecord.application_id == selected_app_id)
            .options(selectinload(InterviewRecord.question_items))
            .order_by(InterviewRecord.scheduled_at.desc())
        ).all()
    )

    if not interviews:
        st.info("No interviews logged for this application yet.")
        return

    for iv in interviews:
        with st.container(border=True):
            st.subheader(f"{iv.stage} ({iv.format}) — {format_dt_in_tz(iv.scheduled_at, tz_name)}")
            st.caption(f"Participants: {iv.participants or 'Not specified'}")

            checklist_items = json.loads(iv.prep_checklist_json or "[]")
            st.markdown("**Preparation Checklist**")
            updated_checklist = []
            for idx, item in enumerate(checklist_items):
                checked = st.checkbox(
                    item["item"],
                    value=bool(item.get("done")),
                    key=f"iv_chk_{iv.id}_{idx}",
                )
                updated_checklist.append({"item": item["item"], "done": checked})

            with st.form(f"iv_details_form_{iv.id}"):
                new_chk_item = st.text_input("Add Checklist Item (optional)")
                q_to_ask = st.text_area("Questions to Ask the Interviewer", value=iv.questions_to_ask or "", height=80)
                col_f1, col_f2 = st.columns(2)
                feedback = col_f1.text_area("Feedback Received / Signals", value=iv.feedback or "", height=100)
                reflection = col_f2.text_area("Personal Reflection", value=iv.reflection or "", height=100)
                follow_ups = st.text_area("Follow-up Actions", value=iv.follow_up_actions or "", height=70)

                if st.form_submit_button("Save Checklist, Notes & Reflection"):
                    if new_chk_item.strip():
                        updated_checklist.append({"item": new_chk_item.strip(), "done": False})
                    ApplicationService.update_interview_details(
                        session=session,
                        interview_id=iv.id,
                        checklist_items=updated_checklist,
                        questions_to_ask=q_to_ask,
                        feedback=feedback,
                        reflection=reflection,
                        follow_up_actions=follow_ups,
                    )
                    st.success("Interview workspace updated!")
                    st.rerun()

            st.divider()
            st.markdown("#### Practice Questions vs. Confirmed Asked Questions")

            practice_qs = [q for q in iv.question_items if q.origin in ("ai_practice", "user_practice")]
            confirmed_qs = [q for q in iv.question_items if q.origin == "confirmed_asked"]

            q_col1, q_col2 = st.columns(2)
            with q_col1:
                st.markdown("**Practice Bank (AI-Generated & User Practice)**")
                if not practice_qs:
                    st.caption("No practice questions added yet.")
                for pq in practice_qs:
                    st.markdown(
                        f"**[{pq.category}]** {pq.question_text} {render_origin_badge(pq.origin)}",
                        unsafe_allow_html=True,
                    )
                    st.caption(f"Answer Notes: {pq.answer_notes or '—'}")
                    if st.button("Mark as Confirmed Asked in Interview", key=f"promote_q_{pq.id}"):
                        ApplicationService.update_interview_question(
                            session, pq.id, "confirmed_asked", pq.answer_notes
                        )
                        st.rerun()

            with q_col2:
                st.markdown("**Confirmed Asked in Actual Interview**")
                if not confirmed_qs:
                    st.caption("No questions confirmed as asked yet.")
                for cq in confirmed_qs:
                    st.markdown(
                        f"**[{cq.category}]** {cq.question_text} {render_origin_badge(cq.origin)}",
                        unsafe_allow_html=True,
                    )
                    st.caption(f"My Answer / Notes: {cq.answer_notes or '—'}")
                    if st.button("Move back to Practice", key=f"demote_q_{cq.id}"):
                        ApplicationService.update_interview_question(
                            session, cq.id, "user_practice", cq.answer_notes
                        )
                        st.rerun()

            with st.form(f"add_question_form_{iv.id}"):
                st.markdown("**Add Question to This Interview**")
                qc1, qc2 = st.columns(2)
                q_cat = qc1.selectbox("Category", ["Technical", "Behavioral", "General"])
                q_origin = qc2.selectbox(
                    "Question Status / Origin",
                    ["user_practice", "ai_practice", "confirmed_asked"],
                    format_func=lambda x: {
                        "user_practice": "User Practice Question",
                        "ai_practice": "AI-Generated Practice Question",
                        "confirmed_asked": "Confirmed Asked in Interview",
                    }[x],
                )
                q_text = st.text_input("Question Text *")
                q_ans = st.text_area("My Answer Notes", height=70)
                if st.form_submit_button("Add Question"):
                    if q_text.strip():
                        ApplicationService.add_interview_question(
                            session, iv.id, q_cat, q_origin, q_text, q_ans
                        )
                        st.success("Question recorded!")
                        st.rerun()