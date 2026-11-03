import json
import time
from datetime import date, timedelta
import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.models import (
    JobApplication,
    Skill,
    LearningGoal,
    NoteItem,
    Document,
    ProfileEntry,
    ChatSession,
    ChatMessage,
)
from src.schemas import (
    JobAnalysisOutput,
    QuizGenerationOutput,
    StudyPlanOutput,
    AnswerCoachOutput,
)
from src.services.application_service import ApplicationService
from src.services.learning_service import LearningService
from src.services.document_service import DocumentService
from src.services.ollama_service import OllamaService
from src.services.request_guard import claim_request, finish_request
from src.ui.helpers import get_active_ollama_model, get_active_ollama_base_url


ASSISTANT_MODES = [
    "Tutor",
    "Quiz",
    "Mock interview",
    "Answer coach",
    "Job analysis",
    "Study planner",
]


def render_assistant_view(session: Session) -> None:
    model_name = get_active_ollama_model(session)
    base_url = get_active_ollama_base_url(session)
    ollama = OllamaService(base_url=base_url, model_name=model_name)

    st.title("Local Ollama Career & Learning Assistant")
    st.caption(
        f"Powered locally by Ollama (`{model_name}` at `{base_url}`). No external LLM API key required."
    )

    # Mode and Context Selection
    apps = list(session.scalars(select(JobApplication).order_by(JobApplication.company.asc())).all())
    skills = list(session.scalars(select(Skill).order_by(Skill.name.asc())).all())
    goals = list(session.scalars(select(LearningGoal).order_by(LearningGoal.title.asc())).all())
    notes = list(session.scalars(select(NoteItem).order_by(NoteItem.created_at.desc())).all())
    docs = list(session.scalars(select(Document).order_by(Document.created_at.desc())).all())
    profile_entries = list(session.scalars(select(ProfileEntry)).all())

    app_map = {a.id: f"{a.company} — {a.role}" for a in apps}
    skill_map = {s.id: s.name for s in skills}
    goal_map = {g.id: g.title for g in goals}
    doc_map = {d.id: f"{d.title} ({d.version_label})" for d in docs}
    note_map = {n.id: n.title for n in notes}

    default_mode = st.session_state.get("assistant_mode", "Tutor")
    default_app_id = st.session_state.get("selected_app_id", None)

    with st.container(border=True):
        st.subheader("Active Mode & Selected Context")
        mc1, mc2, mc3, mc4 = st.columns(4)
        selected_mode = mc1.selectbox(
            "Assistant Mode",
            ASSISTANT_MODES,
            index=ASSISTANT_MODES.index(default_mode) if default_mode in ASSISTANT_MODES else 0,
        )
        app_options = [None] + list(app_map.keys())
        selected_app_id = mc2.selectbox(
            "Application Context",
            app_options,
            index=app_options.index(default_app_id) if default_app_id in app_options else 0,
            format_func=lambda x: "None" if x is None else app_map[x],
        )
        selected_skill_id = mc3.selectbox(
            "Topic / Skill",
            [None] + list(skill_map.keys()),
            format_func=lambda x: "None" if x is None else skill_map[x],
        )
        selected_goal_id = mc4.selectbox(
            "Learning Goal",
            [None] + list(goal_map.keys()),
            format_func=lambda x: "None" if x is None else goal_map[x],
        )

        dc1, dc2, dc3 = st.columns([2, 2, 1])
        selected_doc_ids = dc1.multiselect(
            "Include Uploaded Documents (CVs, Study Notes, Reference PDFs)",
            options=list(doc_map.keys()),
            format_func=lambda x: doc_map[x],
        )
        selected_note_ids = dc2.multiselect(
            "Include Saved Notes",
            options=list(note_map.keys()),
            format_func=lambda x: note_map[x],
        )
        include_profile = dc3.checkbox("Include Experience Bank", value=True)

        active_badges = [
            f"**Mode:** `{selected_mode}`",
            f"**Provider:** `ollama`",
            f"**Model:** `{model_name}`",
        ]
        if selected_app_id:
            active_badges.append(f"**App:** `{app_map[selected_app_id]}`")
        if selected_skill_id:
            active_badges.append(f"**Skill:** `{skill_map[selected_skill_id]}`")
        if selected_doc_ids:
            active_badges.append(f"**Docs:** `{len(selected_doc_ids)} selected`")
        st.caption(" | ".join(active_badges))

    # Session Management
    existing_sessions = list(
        session.scalars(
            select(ChatSession)
            .where(ChatSession.mode == selected_mode)
            .options(selectinload(ChatSession.messages))
            .order_by(ChatSession.updated_at.desc())
        ).all()
    )

    sc_col1, sc_col2 = st.columns([3, 1])
    session_options = [None] + [s.id for s in existing_sessions]
    session_labels = {s.id: f"{s.title} ({len(s.messages)} msgs)" for s in existing_sessions}
    active_session_id = sc_col1.selectbox(
        f"Saved '{selected_mode}' Sessions",
        session_options,
        format_func=lambda x: "➕ Start New Session" if x is None else session_labels[x],
    )
    if sc_col2.button("New Session", use_container_width=True):
        active_session_id = None
        st.rerun()

    current_chat_session = session.get(ChatSession, active_session_id) if active_session_id else None

    # Render previous messages and interactive proposal cards
    if current_chat_session:
        for msg in current_chat_session.messages:
            with st.chat_message(msg.role):
                if msg.was_context_truncated:
                    st.warning("⚠️ Selected context exceeded the size limit and was partially truncated.")
                st.markdown(msg.content)
                message_metrics = st.session_state.get("ollama_message_metrics", {}).get(str(msg.id))
                if message_metrics:
                    st.caption(_format_request_metrics(message_metrics))
                elif msg.total_tokens:
                    st.caption(
                        f"Model: `{msg.model_name}` | Prompt tokens: `{msg.prompt_tokens}` | "
                        f"Output tokens: `{msg.output_tokens}` | Total tokens: `{msg.total_tokens}`"
                    )
                if msg.role == "assistant":
                    _render_message_actions(
                        session=session,
                        msg=msg,
                        mode=selected_mode,
                        app_id=selected_app_id,
                        skill_id=selected_skill_id,
                        goal_id=selected_goal_id,
                    )

    # Mode-Specific Controls & Prompt Input
    _render_mode_prompt_box(
        session=session,
        ollama=ollama,
        mode=selected_mode,
        chat_session=current_chat_session,
        profile_entries=profile_entries,
        include_profile=include_profile,
        app_id=selected_app_id,
        skill_id=selected_skill_id,
        goal_id=selected_goal_id,
        doc_ids=selected_doc_ids,
        note_ids=selected_note_ids,
    )


def _assemble_selected_context(
    session: Session,
    app_id: int | None,
    skill_id: int | None,
    goal_id: int | None,
    doc_ids: list[int],
    note_ids: list[int],
    include_profile: bool,
    profile_entries: list[ProfileEntry],
) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    if app_id:
        app = session.get(JobApplication, app_id)
        if app:
            sections.append(
                {
                    "label": f"Job Application: {app.company} - {app.role}",
                    "content": (
                        f"Company: {app.company}\nRole: {app.role}\nLocation: {app.location}\n"
                        f"Status: {app.status}\nJob Description:\n{app.job_description or 'None provided.'}"
                    ),
                }
            )
    if skill_id:
        metrics = LearningService.get_skill_metrics(session, skill_id)
        sections.append(
            {
                "label": f"Selected Skill: {metrics['name']}",
                "content": json.dumps(metrics, indent=2),
            }
        )
    if goal_id:
        goal = session.get(LearningGoal, goal_id)
        if goal:
            sections.append(
                {
                    "label": f"Learning Goal: {goal.title}",
                    "content": f"Type: {goal.goal_type}\nTarget Date: {goal.target_date}\nDescription: {goal.description}",
                }
            )
    if include_profile and profile_entries:
        prof_lines = []
        for p in profile_entries:
            prof_lines.append(
                f"[{p.category}] {p.title} ({p.organization or ''}, {p.date_range or ''})\n"
                f"Role/Skill: {p.role_or_skill or ''}\nDescription: {p.description or ''}\n"
                f"STAR: S={p.situation or ''} | T={p.task or ''} | A={p.action or ''} | R={p.result or ''}\n"
                f"Evidence: {p.evidence or ''}"
            )
        sections.append({"label": "User Experience Bank & Profile", "content": "\n\n".join(prof_lines)})

    for d_id in doc_ids:
        doc = session.get(Document, d_id)
        if doc:
            sections.append(
                {
                    "label": f"Document: {doc.title} ({doc.version_label})",
                    "content": DocumentService.format_document_for_context(doc),
                }
            )
    for n_id in note_ids:
        note = session.get(NoteItem, n_id)
        if note:
            sections.append({"label": f"Saved Note: {note.title}", "content": note.content})

    return sections


def _render_mode_prompt_box(
    session: Session,
    ollama: OllamaService,
    mode: str,
    chat_session: ChatSession | None,
    profile_entries: list[ProfileEntry],
    include_profile: bool,
    app_id: int | None,
    skill_id: int | None,
    goal_id: int | None,
    doc_ids: list[int],
    note_ids: list[int],
) -> None:
    st.divider()
    failed_request = st.session_state.get("assistant_failed_request")
    if failed_request and failed_request.get("mode") == mode:
        with st.chat_message("assistant"):
            if failed_request.get("partial_text"):
                st.markdown(failed_request["partial_text"])
            if failed_request.get("response_complete"):
                st.warning("The response was generated but could not be saved. Use retry to try again.")
            else:
                st.warning("This response is incomplete and was not saved. Use the retry button to request it again.")
            st.error(f"AI Error ({failed_request.get('error_type')}): {failed_request.get('error_message')}")
            if failed_request.get("metrics"):
                st.caption(_format_request_metrics(failed_request["metrics"]))

    with st.form(f"assistant_prompt_form_{mode}"):
        response_depth = st.segmented_control(
            "Response depth",
            options=["Quick", "Detailed"],
            default="Quick",
            key=f"assistant_response_depth_{mode}",
        )
        st.caption(
            "Quick limits generation length for faster local inference on qwen2.5:0.5b; Detailed allows up to OLLAMA_OUTPUT_TOKENS."
        )
        source_options = [
            "My materials (no web search)",
            "Combine my materials + web",
            "Search the web",
        ]
        source_mode = st.selectbox(
            "Sources",
            source_options,
            index=0,
            key=f"assistant_sources_{mode}",
        )
        st.caption(
            "Local materials use zero external APIs. Web search modes use Firecrawl when FIRECRAWL_API_KEY is configured."
        )

        if mode == "Tutor":
            level = st.selectbox("Explanation Level", ["Beginner", "Intermediate", "Senior / Deep Technical"])
            user_input = st.text_area(
                "Ask a concept question or respond to the Tutor's follow-up:",
                placeholder="Explain how SQLAlchemy's identity map prevents duplicate in-memory state...",
            )
            sys_inst = (
                f"Mode: Tutor (Level: {level}). Explain concepts clearly at the {level} level, give concrete examples, "
                "cite supplied documents with page numbers when applicable, and end with one short follow-up question."
            )
        elif mode == "Quiz":
            num_q = st.slider("Number of Questions", min_value=1, max_value=5, value=2)
            user_input = st.text_input(
                "Quiz Focus / Instructions",
                value="Generate practice questions from the selected topic and reference materials.",
            )
            sys_inst = (
                f"Mode: Quiz Generator. Generate {num_q} multiple-choice questions based on the selected topic/materials. "
                "Each question must have exactly 4 options and a valid correct_option_index (0..3)."
            )
        elif mode == "Mock interview":
            stage_focus = st.selectbox("Interview Focus", ["Technical & Architecture", "Behavioral (STAR)", "Mixed"])
            user_input = st.text_area(
                "Start the mock interview or reply to the interviewer's current question:",
                placeholder="Start the interview by asking me the first question, or evaluate my answer above...",
            )
            sys_inst = (
                f"Mode: Mock Interview ({stage_focus}). Ask strictly ONE question at a time grounded in the selected job "
                "description and user profile. Provide concise feedback when requested."
            )
        elif mode == "Answer coach":
            question_asked = st.text_input("Interview Question *", placeholder="Tell me about a time you resolved a production outage...")
            draft_answer = st.text_area("Your Draft Answer *", height=120)
            user_input = f"Interview Question: {question_asked}\n\nUser's Draft Answer:\n{draft_answer}"
            sys_inst = (
                "Mode: Answer Coach. Critique and improve the user's draft answer using ONLY facts present in the draft and Experience Bank. "
                "Never invent metrics or achievements."
            )
        elif mode == "Job analysis":
            user_input = st.text_area(
                "Job Analysis Focus",
                value="Extract explicit requirements, separate required vs preferred skills, and compare against my Experience Bank.",
            )
            sys_inst = (
                "Mode: Job Analysis. Separate explicit requirements from inferences, classify Required vs Preferred skills, "
                "and compare with the user's profile. Mark unverified skills as 'Missing / Unknown'."
            )
        else:  # Study planner
            avail_hours = st.number_input("Available Study Hours per Week", min_value=1, max_value=60, value=8)
            user_input = st.text_area(
                "Planning Preferences & Deadlines",
                value=f"Create an editable study plan based on my selected goals, deadlines, and {avail_hours} hours/week.",
            )
            sys_inst = "Mode: Study Planner. Generate a concise milestone study schedule and proposed tasks."

        submitted = st.form_submit_button(f"Run {mode}", type="primary", disabled=not ollama.is_configured())

    retry_payload = st.session_state.get("assistant_retry_payload")
    retry_clicked = bool(
        retry_payload
        and retry_payload.get("mode") == mode
        and st.button("Retry last failed request", disabled=not ollama.is_configured(), key=f"retry_ai_{mode}")
    )
    is_retry = False
    if retry_clicked:
        is_retry = True
        submitted = True
        user_input = retry_payload["user_input"]
        sys_inst = retry_payload["system_instruction"]
        response_depth = retry_payload["response_depth"]
        source_mode = retry_payload.get("source_mode", "My materials (no web search)")
        app_id = retry_payload["app_id"]
        skill_id = retry_payload["skill_id"]
        goal_id = retry_payload["goal_id"]
        doc_ids = retry_payload["doc_ids"]
        note_ids = retry_payload["note_ids"]
        include_profile = retry_payload["include_profile"]
        chat_session = session.get(ChatSession, retry_payload.get("chat_session_id"))

    if submitted and user_input.strip():
        if response_depth not in {"Quick", "Detailed"}:
            response_depth = "Quick"
        request_payload = {
            "mode": mode,
            "user_input": user_input.strip(),
            "system_instruction": sys_inst,
            "response_depth": response_depth,
            "source_mode": source_mode,
            "app_id": app_id,
            "skill_id": skill_id,
            "goal_id": goal_id,
            "doc_ids": list(doc_ids),
            "note_ids": list(note_ids),
            "include_profile": include_profile,
            "chat_session_id": chat_session.id if chat_session else None,
        }
        with st.chat_message("user"):
            st.markdown(user_input.strip())

        with st.status("Preparing selected context", expanded=False) as progress:
            preparation_started = time.perf_counter()
            context_sections = _assemble_selected_context(
                session=session,
                app_id=app_id,
                skill_id=skill_id,
                goal_id=goal_id,
                doc_ids=doc_ids,
                note_ids=note_ids,
                include_profile=include_profile,
                profile_entries=profile_entries,
            )
            require_web_only = source_mode == "Search the web"
            if require_web_only:
                context_sections = []
            web_search = source_mode != "My materials (no web search)"
            context_fingerprint = json.dumps(
                [
                    source_mode,
                    chat_session.id if chat_session else None,
                    len(chat_session.messages) if chat_session else 0,
                    context_sections,
                ],
                ensure_ascii=False,
                sort_keys=True,
            )
            req_hash = OllamaService.compute_request_hash(
                mode,
                ollama.model_name,
                user_input.strip(),
                context_fingerprint,
                sys_inst,
                response_depth,
            )
            context_preparation_seconds = time.perf_counter() - preparation_started
            request_states = st.session_state.setdefault("ollama_request_states", {})
            if not claim_request(request_states, req_hash, allow_retry=is_retry):
                progress.update(label="Duplicate request prevented", state="complete")
                st.info(
                    "This identical request has already completed or is already running. Use a new prompt or context to start another request."
                )
                return

            st.session_state.pop("assistant_failed_request", None)
            progress.update(label=f"Waiting for Ollama ({ollama.model_name})", state="running")

            def update_stage(stage: str) -> None:
                progress.update(label=stage, state="running")

            try:
                with st.spinner(f"Running local Ollama ({ollama.model_name})", show_time=True):
                    if mode == "Job analysis":
                        result = ollama.generate_structured(
                            user_input,
                            JobAnalysisOutput,
                            context_sections,
                            sys_inst,
                            response_depth=response_depth,
                            on_stage=update_stage,
                            web_search=web_search,
                            require_web_only=require_web_only,
                        )
                    elif mode == "Quiz":
                        result = ollama.generate_structured(
                            user_input,
                            QuizGenerationOutput,
                            context_sections,
                            sys_inst,
                            response_depth=response_depth,
                            on_stage=update_stage,
                            web_search=web_search,
                            require_web_only=require_web_only,
                        )
                    elif mode == "Study planner":
                        result = ollama.generate_structured(
                            user_input,
                            StudyPlanOutput,
                            context_sections,
                            sys_inst,
                            response_depth=response_depth,
                            on_stage=update_stage,
                            web_search=web_search,
                            require_web_only=require_web_only,
                        )
                    elif mode == "Answer coach":
                        result = ollama.generate_structured(
                            user_input,
                            AnswerCoachOutput,
                            context_sections,
                            sys_inst,
                            response_depth=response_depth,
                            on_stage=update_stage,
                            web_search=web_search,
                            require_web_only=require_web_only,
                        )
                    else:
                        history = (
                            [{"role": m.role, "content": m.content} for m in chat_session.messages]
                            if chat_session and not require_web_only
                            else []
                        )
                        with st.chat_message("assistant"):
                            streaming_call = ollama.generate_text_stream(
                                user_input,
                                context_sections,
                                sys_inst,
                                chat_history=history,
                                response_depth=response_depth,
                                on_stage=update_stage,
                                web_search=web_search,
                                require_web_only=require_web_only,
                            )
                            st.write_stream(streaming_call)
                            result = streaming_call.result
                            if not result.success:
                                st.warning("Incomplete response — this text has not been saved.")
                                st.error(f"AI Error ({result.error_type}): {result.error_message}")

                result.context_preparation_seconds += context_preparation_seconds
                metrics = _request_metrics(result)
                _record_request_metrics(metrics)
                if not result.success or (
                    mode in {"Job analysis", "Quiz", "Study planner", "Answer coach"}
                    and result.structured_data is None
                ):
                    finish_request(request_states, req_hash, success=False)
                    if mode not in {"Tutor", "Mock interview"}:
                        st.error(
                            f"AI Error ({result.error_type or 'invalid_structured_output'}): "
                            f"{result.error_message or 'The structured result did not pass validation.'}"
                        )
                    st.session_state["assistant_failed_request"] = {
                        **request_payload,
                        "partial_text": result.text if mode in {"Tutor", "Mock interview"} else "",
                        "error_type": result.error_type or "invalid_structured_output",
                        "error_message": result.error_message or "The structured result did not pass validation.",
                        "response_complete": result.success,
                        "metrics": metrics,
                    }
                    st.session_state["assistant_retry_payload"] = request_payload
                    st.caption(_format_request_metrics(metrics))
                    progress.update(label="Failed", state="error")
                    return

                if result.truncation_notice:
                    st.warning(result.truncation_notice)
                progress.update(label="Saving result", state="running")

                if not chat_session:
                    chat_session = ChatSession(
                        title=f"{mode}: {user_input.strip()[:45]}",
                        mode=mode,
                        application_id=app_id,
                        learning_goal_id=goal_id,
                        skill_id=skill_id,
                        selected_doc_ids_json=json.dumps(doc_ids),
                        selected_note_ids_json=json.dumps(note_ids),
                    )
                    session.add(chat_session)
                    session.flush()

                formatted_md = _format_structured_result_to_markdown(mode, result)
                formatted_md += OllamaService.grounding_markdown(result)
                structured_payload = (
                    result.structured_data.model_dump_json() if result.structured_data is not None else None
                )
                if result.web_search_enabled:
                    payload = json.loads(structured_payload) if structured_payload else {}
                    payload["_web_grounding"] = {
                        "source_mode": source_mode,
                        "search_used": result.search_used,
                        "sources": result.web_sources,
                        "search_error": result.search_error,
                    }
                    structured_payload = json.dumps(payload)
                session.add(
                    ChatMessage(
                        session_id=chat_session.id,
                        role="user",
                        content=user_input.strip(),
                    )
                )
                assistant_message = ChatMessage(
                    session_id=chat_session.id,
                    role="assistant",
                    content=formatted_md,
                    structured_json=structured_payload,
                    was_context_truncated=result.was_truncated,
                    model_name=result.model_used,
                    prompt_tokens=result.prompt_tokens,
                    output_tokens=result.output_tokens,
                    total_tokens=result.total_tokens,
                )
                session.add(assistant_message)
                session.flush()
                assistant_message_id = assistant_message.id
                session.commit()
                finish_request(request_states, req_hash, success=True)
                st.session_state.pop("assistant_retry_payload", None)
                st.session_state.pop("assistant_failed_request", None)
                message_metrics = st.session_state.setdefault("ollama_message_metrics", {})
                message_metrics[str(assistant_message_id)] = metrics
                progress.update(label="Completed", state="complete")
                st.rerun()
            except Exception as exc:
                session.rollback()
                finish_request(request_states, req_hash, success=False)
                st.session_state["assistant_retry_payload"] = request_payload
                error_message = f"Could not save the Ollama result: {type(exc).__name__}: {exc}"
                st.session_state["assistant_failed_request"] = {
                    **request_payload,
                    "partial_text": (
                        result.text
                        if "result" in locals() and mode in {"Tutor", "Mock interview"}
                        else ""
                    ),
                    "error_type": "save_error",
                    "error_message": error_message,
                    "response_complete": "result" in locals() and result.success,
                    "metrics": _request_metrics(result) if "result" in locals() else {},
                }
                st.error(error_message)
                if "result" in locals():
                    st.caption(_format_request_metrics(_request_metrics(result)))
                progress.update(label="Failed", state="error")


def _request_metrics(result) -> dict[str, int | float | None]:
    return {
        "context_preparation_seconds": result.context_preparation_seconds,
        "time_to_first_text_seconds": result.time_to_first_text_seconds,
        "total_request_seconds": result.total_request_seconds,
        "retry_count": result.retry_count,
        "prompt_tokens": result.prompt_tokens,
        "output_tokens": result.output_tokens,
        "total_tokens": result.total_tokens,
    }


def _format_request_metrics(metrics: dict[str, int | float | None]) -> str:
    first_text = metrics.get("time_to_first_text_seconds")
    usage = "Token usage unavailable"
    if metrics.get("total_tokens") is not None:
        usage = (
            f"Tokens: input {metrics.get('prompt_tokens') or 0}, "
            f"output {metrics.get('output_tokens') or 0}, total {metrics.get('total_tokens')}"
        )
    first_text_label = f"{first_text:.2f}s" if first_text is not None else "not streamed"
    return (
        f"Context prep: {metrics.get('context_preparation_seconds', 0):.2f}s · "
        f"Time to first text: {first_text_label} · "
        f"Ollama inference: {metrics.get('total_request_seconds', 0):.2f}s · "
        f"Retries: {metrics.get('retry_count', 0)} · {usage}"
    )


def _record_request_metrics(metrics: dict[str, int | float | None]) -> None:
    history = st.session_state.setdefault("ollama_performance_metrics", [])
    history.append(metrics)
    del history[:-20]


def _format_structured_result_to_markdown(mode: str, result) -> str:
    data = result.structured_data
    if data is None:
        return result.text

    if mode == "Job analysis" and isinstance(data, JobAnalysisOutput):
        lines = [
            f"### Role Summary\n{data.role_summary}",
            "### Explicit Source Requirements\n" + ("\n".join(f"- {r}" for r in data.explicit_requirements) or "- None stated"),
            "### AI Inferences (Distinct from Source Text)\n" + ("\n".join(f"- {i}" for i in data.ai_inferences) or "- None"),
            "### Skill Breakdown & Profile Evidence Comparison",
        ]
        for sb in data.skill_breakdown:
            lines.append(
                f"- **{sb.skill_name}** (`{sb.requirement_level}` | `{sb.source_type}`)\n"
                f"  - *Source:* {sb.source_quote_or_reason}\n"
                f"  - *Profile Match (`{sb.profile_evidence_status}`):* {sb.profile_evidence_detail}"
            )
        lines.append("### Unknowns & Unverified Gaps\n" + ("\n".join(f"- ❓ {u}" for u in data.unknowns_and_gaps) or "- None"))
        return "\n\n".join(lines)

    if mode == "Quiz" and isinstance(data, QuizGenerationOutput):
        lines = [f"### Generated Quiz: {data.topic_summary}"]
        if data.unsupported_material_notice:
            lines.append(f"> ⚠️ **Material Notice:** {data.unsupported_material_notice}")
        lines.append(
            f"*{len(data.questions)} question(s) generated. Click **Save Quiz to Learning Hub** below to take the quiz with hidden answers.*"
        )
        for idx, q in enumerate(data.questions, start=1):
            opts_str = "\n".join(f"  {chr(65+i)}. {opt}" for i, opt in enumerate(q.options))
            lines.append(f"**Q{idx}: {q.question_text}**\n{opts_str}")
        return "\n\n".join(lines)

    if mode == "Study planner" and isinstance(data, StudyPlanOutput):
        lines = [f"### {data.plan_title}", f"**Rationale:** {data.rationale}", "### Editable Schedule Milestones"]
        for m in data.milestones:
            acts = ", ".join(m.activities)
            lines.append(f"- **{m.day_or_week_label} — {m.focus_topic}** ({m.estimated_minutes} mins): {acts}")
        return "\n\n".join(lines)

    if mode == "Answer coach" and isinstance(data, AnswerCoachOutput):
        lines = [
            "### Strengths in Your Draft\n" + "\n".join(f"- ✅ {s}" for s in data.critique_strengths),
            "### Gaps to Address\n" + "\n".join(f"- 🔍 {g}" for g in data.critique_gaps),
            f"### Improved Draft (Strictly Preserving Your Experience)\n{data.improved_draft}",
            "### Clarifying Details You Can Add (No Invented Facts)\n"
            + ("\n".join(f"- ❓ {u}" for u in data.unverified_placeholders_needed) or "- None"),
        ]
        return "\n\n".join(lines)

    return result.text


def _render_message_actions(
    session: Session,
    msg: ChatMessage,
    mode: str,
    app_id: int | None,
    skill_id: int | None,
    goal_id: int | None,
) -> None:
    col_a, col_b = st.columns([1, 3])
    if col_a.button("📝 Save Response as Note", key=f"save_note_msg_{msg.id}"):
        LearningService.save_note(
            session=session,
            title=f"AI {mode} Note ({msg.created_at.strftime('%Y-%m-%d %H:%M')})",
            content=msg.content,
            origin="AI Saved Output",
            application_id=app_id,
            learning_goal_id=goal_id,
            skill_id=skill_id,
        )
        st.success("Saved response as a study note!")

    if not msg.structured_json:
        return

    try:
        raw = json.loads(msg.structured_json)
    except json.JSONDecodeError:
        return

    # Proposed Tasks Review & Explicit Save
    proposed_tasks = raw.get("proposed_tasks", [])
    if proposed_tasks:
        with st.expander(f"📋 Review & Save Proposed Tasks ({len(proposed_tasks)})"):
            st.caption("AI suggestions are never saved automatically. Review and click to save individual tasks:")
            for idx, pt in enumerate(proposed_tasks):
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"**[{pt.get('task_type', 'Study')}] {pt.get('title')}** — {pt.get('description', '')}")
                if c2.button("Save Task", key=f"save_pt_{msg.id}_{idx}"):
                    due = date.today() + timedelta(days=int(pt.get("suggested_due_days") or 3))
                    ApplicationService.create_task(
                        session=session,
                        title=pt.get("title", "Study Task"),
                        description=pt.get("description", ""),
                        task_type=pt.get("task_type", "Study"),
                        due_date=due,
                        origin="AI Proposal",
                        application_id=app_id,
                        learning_goal_id=goal_id,
                        skill_id=skill_id,
                    )
                    st.success(f"Saved task: {pt.get('title')}")

    # Job Analysis Skill Links Proposal
    skill_breakdown = raw.get("skill_breakdown", [])
    if skill_breakdown and app_id:
        with st.expander(f"🔗 Link Extracted Skills to Application ({len(skill_breakdown)})"):
            st.caption("Explicitly confirm which extracted skills to link to this application record:")
            if st.button("Save Extracted Skills to Application", key=f"link_skills_msg_{msg.id}"):
                for sb in skill_breakdown:
                    ApplicationService.link_skill_to_application(
                        session=session,
                        application_id=app_id,
                        skill_name=sb["skill_name"],
                        requirement_level=sb["requirement_level"],
                        source_type=sb["source_type"],
                        evidence_snippet=sb["source_quote_or_reason"],
                    )
                st.success("Linked extracted skills to the application!")

    # Quiz Questions Save
    quiz_questions = raw.get("questions", [])
    if quiz_questions:
        if col_b.button("🎯 Save Quiz Questions to Learning Hub", key=f"save_quiz_msg_{msg.id}"):
            for q in quiz_questions:
                LearningService.create_quiz_question(
                    session=session,
                    question_text=q["question_text"],
                    options=q["options"],
                    correct_option_index=q["correct_option_index"],
                    explanation=q["explanation"],
                    skill_id=skill_id,
                    learning_goal_id=goal_id,
                    source_citation=q.get("source_citation"),
                    suggested_revisit_topic=q.get("suggested_revisit_topic"),
                )
            st.success("Quiz saved to Learning Hub! Open Learning -> Practice Quizzes to test yourself.")