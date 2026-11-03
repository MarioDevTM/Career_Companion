import json
from datetime import date, timedelta
import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import (
    Skill,
    JobApplication,
    StudyResource,
    NoteItem,
    TaskItem,
    QuizQuestion,
    RevisionItem,
)
from src.services.application_service import ApplicationService
from src.services.learning_service import LearningService, REVISION_STAGE_INTERVALS
from src.ui.helpers import render_origin_badge


def render_learning_view(session: Session) -> None:
    st.title("Learning Hub & Certification Prep")
    st.caption(
        "Track skills, multi-application or independent certification goals, study sessions, quizzes, and spaced revision. "
        "Self-reported confidence is tracked separately from empirical practice performance."
    )

    tabs = st.tabs(
        [
            "Topics & Skills",
            "Learning Goals & Resources",
            "Study Sessions, Notes & Tasks",
            "Practice Quizzes",
            "Flashcards & Revision Schedule",
        ]
    )

    skills = list(session.scalars(select(Skill).order_by(Skill.name.asc())).all())
    goals = LearningService.list_learning_goals(session)
    apps = list(session.scalars(select(JobApplication).order_by(JobApplication.company.asc())).all())

    skill_map = {s.id: s.name for s in skills}
    goal_map = {g.id: f"{g.title} [{g.goal_type}]" for g in goals}
    app_map = {a.id: f"{a.company} — {a.role}" for a in apps}

    # TAB 1: Topics & Skills
    with tabs[0]:
        with st.expander("➕ Add or Update Skill / Topic", expanded=not bool(skills)):
            with st.form("skill_form"):
                sc1, sc2, sc3 = st.columns([2, 1, 1])
                s_name = sc1.text_input("Skill / Topic Name *", placeholder="e.g., SQLAlchemy 2.0, AWS IAM, System Design")
                s_cat = sc2.selectbox("Category", ["Technical", "Certification", "Architecture", "Behavioral", "Domain"])
                s_conf = sc3.slider("Self-Reported Confidence (1-5)", min_value=1, max_value=5, value=2)
                if st.form_submit_button("Save Skill"):
                    try:
                        LearningService.create_or_update_skill(session, s_name, s_cat, s_conf)
                        st.success(f"Saved skill: {s_name}")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

        if not skills:
            st.info("No skills tracked yet.")
        else:
            st.info(
                "💡 **Mastery Policy:** Reading a note or passing a single quiz never marks a skill as Mastered. "
                "A skill reaches *Demonstrated Proficiency* only after at least **3 quiz attempts** with **80%+ accuracy** and **60+ minutes** of logged study."
            )
            for s in skills:
                metrics = LearningService.get_skill_metrics(session, s.id)
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 3])
                    c1.markdown(f"**{metrics['name']}** (`{metrics['category']}`)")
                    c2.write(f"Self-Confidence: **{metrics['self_confidence']} / 5**")
                    acc_str = f"{metrics['quiz_accuracy_pct']}% ({metrics['quiz_attempts']} attempts)" if metrics["quiz_accuracy_pct"] is not None else "No attempts"
                    c3.write(f"Practice Score: **{acc_str}**")
                    c4.write(f"Study Time: **{metrics['study_minutes']}m** | Status: `{metrics['evidence_status']}`")

    # TAB 2: Learning Goals & Resources
    with tabs[1]:
        with st.expander("➕ Create Learning or Certification Goal", expanded=not bool(goals)):
            with st.form("learning_goal_form"):
                gc1, gc2, gc3 = st.columns([2, 1, 1])
                g_title = gc1.text_input("Goal Title *", placeholder="e.g., AWS Certified Developer Exam or Backend Interview Prep")
                g_type = gc2.selectbox("Goal Type", ["Job Preparation", "Certification", "General Skill"])
                g_target = gc3.date_input("Target Date (optional)", value=None)
                g_desc = st.text_area("Description / Syllabus Notes", height=70)
                linked_apps = st.multiselect(
                    "Link to Job Applications (leave empty for independent/certification goals)",
                    options=list(app_map.keys()),
                    format_func=lambda x: app_map[x],
                )
                if st.form_submit_button("Create Learning Goal"):
                    if g_title.strip():
                        LearningService.create_learning_goal(
                            session, g_title, g_type, g_desc, g_target, linked_apps
                        )
                        st.success("Learning goal created!")
                        st.rerun()

        for g in goals:
            with st.container(border=True):
                linked_labels = [f"{a.company} ({a.role})" for a in g.applications]
                scope_badge = (
                    f"Linked to: {', '.join(linked_labels)}"
                    if linked_labels
                    else "Independent Goal / Certification"
                )
                st.subheader(f"{g.title} (`{g.goal_type}`) — Target: {g.target_date or 'Flexible'}")
                st.caption(scope_badge)
                if g.description:
                    st.write(g.description)

                if g.resources:
                    st.markdown("**Resource Links:**")
                    for res in g.resources:
                        st.markdown(f"- [{res.title}]({res.url or '#'}) — {res.notes or ''}")

                with st.form(f"add_res_form_{g.id}"):
                    rc1, rc2, rc3 = st.columns(3)
                    r_title = rc1.text_input("Resource Title")
                    r_url = rc2.text_input("URL")
                    r_notes = rc3.text_input("Notes")
                    if st.form_submit_button("Add Resource Link"):
                        if r_title.strip():
                            session.add(
                                StudyResource(
                                    learning_goal_id=g.id,
                                    title=r_title.strip(),
                                    url=r_url.strip() or None,
                                    notes=r_notes.strip() or None,
                                )
                            )
                            session.commit()
                            st.rerun()

    # TAB 3: Study Sessions, Notes & Tasks
    with tabs[2]:
        col_s, col_n = st.columns(2)
        with col_s:
            st.subheader("Log Study Session")
            with st.form("log_study_session_form"):
                ss_goal = st.selectbox(
                    "Learning Goal (optional)",
                    [None] + list(goal_map.keys()),
                    format_func=lambda x: "None" if x is None else goal_map[x],
                )
                ss_skill = st.selectbox(
                    "Skill / Topic (optional)",
                    [None] + list(skill_map.keys()),
                    format_func=lambda x: "None" if x is None else skill_map[x],
                )
                ss_mins = st.number_input("Duration (minutes)", min_value=5, max_value=600, value=45, step=5)
                ss_act = st.selectbox(
                    "Activity Type",
                    ["Reading / Notes", "Hands-on Coding", "Mock Interview / Drills", "Certification Practice"],
                )
                ss_notes = st.text_area("Session Summary Notes", height=70)
                if st.form_submit_button("Log Session", type="primary"):
                    LearningService.log_study_session(
                        session, int(ss_mins), ss_act, ss_notes, ss_goal, ss_skill
                    )
                    st.success("Study session logged!")
                    st.rerun()

            st.subheader("Study Tasks")
            with st.form("add_study_task_form"):
                t_title = st.text_input("Task Title *")
                tc1, tc2 = st.columns(2)
                t_due = tc1.date_input("Target Date", value=date.today() + timedelta(days=2))
                t_goal = tc2.selectbox(
                    "Goal",
                    [None] + list(goal_map.keys()),
                    format_func=lambda x: "None" if x is None else goal_map[x],
                )
                if st.form_submit_button("Add Study Task"):
                    if t_title.strip():
                        ApplicationService.create_task(
                            session,
                            title=t_title,
                            task_type="Study",
                            due_date=t_due,
                            learning_goal_id=t_goal,
                        )
                        st.rerun()

            study_tasks = list(
                session.scalars(select(TaskItem).where(TaskItem.task_type == "Study")).all()
            )
            for st_task in study_tasks:
                chk = st.checkbox(
                    f"{st_task.title} (Due: {st_task.due_date or '—'})",
                    value=(st_task.status == "Done"),
                    key=f"study_tk_{st_task.id}",
                )
                new_st = "Done" if chk else "Todo"
                if new_st != st_task.status:
                    ApplicationService.toggle_task_status(session, st_task.id, new_st)
                    st.rerun()

        with col_n:
            st.subheader("Study Notes")
            with st.form("create_study_note_form"):
                n_title = st.text_input("Note Title *")
                n_skill = st.selectbox(
                    "Related Skill",
                    [None] + list(skill_map.keys()),
                    format_func=lambda x: "None" if x is None else skill_map[x],
                )
                n_content = st.text_area("Note Content (Markdown supported)", height=130)
                if st.form_submit_button("Save Study Note"):
                    if n_title.strip() and n_content.strip():
                        LearningService.save_note(
                            session, n_title, n_content, origin="User Note", skill_id=n_skill
                        )
                        st.success("Note saved!")
                        st.rerun()

            notes = list(session.scalars(select(NoteItem).order_by(NoteItem.created_at.desc())).all())
            for note in notes:
                with st.expander(f"📝 {note.title} ({note.origin})"):
                    st.markdown(render_origin_badge(note.origin), unsafe_allow_html=True)
                    st.markdown(note.content)

    # TAB 4: Practice Quizzes (hides correct answer until submission!)
    with tabs[3]:
        st.subheader("Practice Quizzes")
        st.caption(
            "Correct answers and explanations remain strictly hidden until you submit your answer."
        )
        with st.expander("➕ Create Custom Quiz Question"):
            with st.form("manual_quiz_form"):
                q_skill = st.selectbox(
                    "Skill",
                    [None] + list(skill_map.keys()),
                    format_func=lambda x: "General" if x is None else skill_map[x],
                )
                q_text = st.text_area("Question Prompt *")
                opt0 = st.text_input("Option A *")
                opt1 = st.text_input("Option B *")
                opt2 = st.text_input("Option C *")
                opt3 = st.text_input("Option D *")
                correct_idx = st.selectbox("Correct Option", [0, 1, 2, 3], format_func=lambda i: ["A", "B", "C", "D"][i])
                explanation = st.text_area("Explanation *")
                revisit = st.text_input("Suggested Sub-topic to Revisit if Missed", value="Core fundamentals")
                if st.form_submit_button("Save Quiz Question"):
                    if q_text.strip() and opt0.strip() and opt1.strip():
                        LearningService.create_quiz_question(
                            session,
                            question_text=q_text.strip(),
                            options=[opt0.strip(), opt1.strip(), opt2.strip(), opt3.strip()],
                            correct_option_index=correct_idx,
                            explanation=explanation.strip() or "Review topic notes.",
                            skill_id=q_skill,
                            suggested_revisit_topic=revisit,
                        )
                        st.success("Quiz question added!")
                        st.rerun()

        questions = list(session.scalars(select(QuizQuestion).order_by(QuizQuestion.id.desc())).all())
        if not questions:
            st.info("No quiz questions saved yet. Add one above or generate a quiz in the AI Assistant.")
        else:
            submitted_map = st.session_state.setdefault("submitted_quizzes", {})
            for qq in questions:
                opts = json.loads(qq.options_json)
                with st.container(border=True):
                    st.markdown(f"**Q#{qq.id}: {qq.question_text}**")
                    choice = st.radio(
                        "Choose an answer:",
                        options=list(range(len(opts))),
                        format_func=lambda i, o=opts: o[i],
                        key=f"quiz_radio_{qq.id}",
                    )
                    if st.button("Submit Answer", key=f"quiz_sub_{qq.id}"):
                        att = LearningService.record_quiz_attempt(session, qq.id, choice)
                        submitted_map[qq.id] = {
                            "selected": choice,
                            "is_correct": att.is_correct,
                        }
                        st.rerun()

                    # Reveal answer ONLY after submission in current session
                    if qq.id in submitted_map:
                        res = submitted_map[qq.id]
                        if res["is_correct"]:
                            st.success(f"✅ Correct! Answer: **{opts[qq.correct_option_index]}**")
                        else:
                            st.error(
                                f"❌ Incorrect. Correct Answer: **{opts[qq.correct_option_index]}**"
                            )
                            if qq.suggested_revisit_topic:
                                st.warning(f"📌 Suggested topic to revisit: **{qq.suggested_revisit_topic}**")
                        st.markdown(f"**Explanation:** {qq.explanation}")
                        if qq.source_citation:
                            st.caption(f"Source: {qq.source_citation}")

    # TAB 5: Flashcards & Spaced Revision Schedule
    with tabs[4]:
        st.subheader("Spaced Revision Schedule")
        st.markdown(
            f"**Documented Revision Schedule:** Intervals progress across 6 stages: "
            f"`{', '.join(str(d) + 'd' for d in REVISION_STAGE_INTERVALS)}`. "
            "Rating a review as **Hard** resets the interval to `1d`; **Good** advances 1 stage; **Easy** advances 2 stages. "
            "You can also manually reschedule any item."
        )

        with st.expander("➕ Add Flashcard / Revision Question"):
            with st.form("create_revision_form"):
                rv_skill = st.selectbox(
                    "Skill",
                    [None] + list(skill_map.keys()),
                    format_func=lambda x: "General" if x is None else skill_map[x],
                )
                front = st.text_input("Question / Front Prompt *")
                back = st.text_area("Answer / Back Explanation *")
                next_dt = st.date_input("Initial Review Date", value=date.today())
                if st.form_submit_button("Add Revision Card"):
                    if front.strip() and back.strip():
                        LearningService.create_revision_item(
                            session, front, back, skill_id=rv_skill, initial_review_date=next_dt
                        )
                        st.success("Revision card added!")
                        st.rerun()

        revisions = list(
            session.scalars(select(RevisionItem).order_by(RevisionItem.next_review_date.asc())).all()
        )
        revealed_cards = st.session_state.setdefault("revealed_flashcards", set())

        for rev in revisions:
            is_due = rev.next_review_date <= date.today()
            due_badge = "🔥 **DUE NOW**" if is_due else f"📅 Scheduled: `{rev.next_review_date}`"
            with st.container(border=True):
                st.markdown(
                    f"{due_badge} | Stage {rev.stage_index + 1} (`{rev.interval_days}d` interval) | Reviews: {rev.review_count}"
                )
                st.markdown(f"**Prompt:** {rev.prompt_front}")

                if st.button("Show / Hide Answer", key=f"rev_show_{rev.id}"):
                    if rev.id in revealed_cards:
                        revealed_cards.remove(rev.id)
                    else:
                        revealed_cards.add(rev.id)
                    st.rerun()

                if rev.id in revealed_cards:
                    st.info(f"**Answer:** {rev.answer_back}")
                    b1, b2, b3 = st.columns(3)
                    if b1.button("😓 Hard (Reset to 1d)", key=f"rev_hard_{rev.id}", use_container_width=True):
                        LearningService.record_revision_review(session, rev.id, "Hard")
                        revealed_cards.discard(rev.id)
                        st.rerun()
                    if b2.button("👍 Good (+1 Stage)", key=f"rev_good_{rev.id}", use_container_width=True):
                        LearningService.record_revision_review(session, rev.id, "Good")
                        revealed_cards.discard(rev.id)
                        st.rerun()
                    if b3.button("🚀 Easy (+2 Stages)", key=f"rev_easy_{rev.id}", use_container_width=True):
                        LearningService.record_revision_review(session, rev.id, "Easy")
                        revealed_cards.discard(rev.id)
                        st.rerun()

                with st.expander("Reschedule Review Date"):
                    new_date = st.date_input(
                        "New Review Date",
                        value=rev.next_review_date,
                        key=f"resched_dt_{rev.id}",
                    )
                    if st.button("Update Date", key=f"resched_btn_{rev.id}"):
                        LearningService.reschedule_revision_item(session, rev.id, new_date)
                        st.success(f"Rescheduled to {new_date}")
                        st.rerun()