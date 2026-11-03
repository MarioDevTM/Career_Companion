from datetime import date
import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import AppConfig, format_dt_in_tz
from src.models import Document
from src.schemas import ApplicationInputSchema
from src.services.application_service import ApplicationService
from src.ui.helpers import get_active_timezone, render_status_badge, navigate_to


def render_applications_view(session: Session) -> None:
    tz_name = get_active_timezone(session)
    st.title("Job Applications")

    docs = list(session.scalars(select(Document).order_by(Document.created_at.desc())).all())
    cv_docs = {d.id: f"{d.title} ({d.version_label})" for d in docs if d.doc_type == "CV"}
    cl_docs = {d.id: f"{d.title} ({d.version_label})" for d in docs if d.doc_type == "Cover Letter"}

    with st.expander(
        "➕ Add New Application",
        expanded=bool(st.session_state.pop("open_new_app_form", False)),
    ):
        _render_application_create_form(session, cv_docs, cl_docs)

    # Search and Filter Controls
    f_col1, f_col2, f_col3, f_col4 = st.columns([2, 2, 1, 1])
    search_q = f_col1.text_input("Search company, role, location, or notes", placeholder="e.g., Python, Bucharest...")
    status_filter = f_col2.multiselect("Filter Statuses", AppConfig.APPLICATION_STATUSES)
    priority_filter = f_col3.selectbox("Priority", ["All"] + AppConfig.PRIORITIES)
    show_archived = f_col4.checkbox("Show Archived", value=False)

    apps = ApplicationService.list_applications(
        session=session,
        search_query=search_q,
        statuses=status_filter or None,
        priority=priority_filter,
        include_archived=show_archived,
    )

    if not apps:
        st.info("No applications match your current filters.")
        return

    st.caption(f"Showing {len(apps)} application(s). Inactivity never automatically marks a role as Rejected.")

    for app in apps:
        badge_html = render_status_badge(app.status)
        archived_tag = " [ARCHIVED]" if app.is_archived else ""
        with st.container(border=True):
            h_col1, h_col2 = st.columns([4, 1])
            with h_col1:
                st.markdown(
                    f"### {app.company} — {app.role}{archived_tag} {badge_html}",
                    unsafe_allow_html=True,
                )
                meta_parts = [
                    f"📍 {app.location or 'Unspecified'} ({app.work_arrangement})",
                    f"💼 {app.employment_type}",
                    f"⚡ Priority: {app.priority}",
                ]
                if app.salary_min or app.salary_max:
                    s_min = f"{app.salary_min:,.0f}" if app.salary_min else "?"
                    s_max = f"{app.salary_max:,.0f}" if app.salary_max else "?"
                    meta_parts.append(
                        f"💶 {s_min} - {s_max} {app.currency} ({app.pay_period}, {app.tax_designation})"
                    )
                st.caption(" | ".join(meta_parts))

            with h_col2:
                if st.button("🤖 Analyze w/ AI", key=f"ai_btn_{app.id}", use_container_width=True):
                    navigate_to("AI Assistant", assistant_mode="Job analysis", selected_app_id=app.id)
                if st.button("🗓️ Interviews", key=f"iv_btn_{app.id}", use_container_width=True):
                    navigate_to("Interviews", selected_app_id=app.id)

            tab_overview, tab_edit, tab_history, tab_contacts, tab_delete = st.tabs(
                ["Overview & Docs", "Edit Record", "Status History", "Contacts & Tasks", "Archive / Delete"]
            )

            with tab_overview:
                c1, c2 = st.columns(2)
                c1.write(f"**Date Applied:** {app.date_applied or 'Not applied yet'}")
                c1.write(f"**Source:** {app.source or '—'}")
                c1.write(f"**Job URL:** {app.job_url or '—'}")
                c1.write(f"**Recruiter:** {app.recruiter_name or '—'} ({app.recruiter_contact or '—'})")
                c2.write(f"**Next Action:** {app.next_action or '—'}")
                c2.write(f"**Next Action Due:** {app.next_action_due or '—'}")
                c2.write(
                    f"**Linked CV:** {app.cv_document.title + ' (' + app.cv_document.version_label + ')' if app.cv_document else 'None'}"
                )
                c2.write(
                    f"**Linked Cover Letter:** {app.cover_letter_document.title + ' (' + app.cover_letter_document.version_label + ')' if app.cover_letter_document else 'None'}"
                )
                if app.notes:
                    st.markdown("**Notes (Saved User Notes):**")
                    st.write(app.notes)
                if app.job_description:
                    with st.expander("View Saved Job Description"):
                        st.text(app.job_description)

            with tab_edit:
                _render_application_edit_form(session, app, cv_docs, cl_docs)

            with tab_history:
                st.caption("Timestamped status progression (never automatically inferred from inactivity):")
                for ev in sorted(app.status_events, key=lambda e: e.changed_at, reverse=True):
                    transition = f"`{ev.old_status}` → `{ev.new_status}`" if ev.old_status else f"Created as `{ev.new_status}`"
                    st.markdown(
                        f"- **{format_dt_in_tz(ev.changed_at, tz_name)}**: {transition} — *{ev.note or ''}*"
                    )

            with tab_contacts:
                st.markdown("**Additional Contacts**")
                for ct in app.contacts:
                    st.markdown(f"- **{ct.name}** ({ct.role or 'Contact'}): `{ct.contact_info or '—'}` — {ct.notes or ''}")
                with st.form(f"add_contact_form_{app.id}"):
                    cc1, cc2, cc3 = st.columns(3)
                    c_name = cc1.text_input("Contact Name")
                    c_role = cc2.text_input("Role")
                    c_info = cc3.text_input("Email / Phone")
                    c_notes = st.text_input("Notes")
                    if st.form_submit_button("Add Contact"):
                        if c_name.strip():
                            ApplicationService.add_contact(session, app.id, c_name, c_role, c_info, c_notes)
                            st.success("Contact added.")
                            st.rerun()

                st.markdown("**Linked Tasks**")
                for tk in app.tasks:
                    done_checked = st.checkbox(
                        f"{tk.title} (Due: {tk.due_date or '—'}) [{tk.status}]",
                        value=(tk.status == "Done"),
                        key=f"app_task_chk_{tk.id}",
                    )
                    target_status = "Done" if done_checked else "Todo"
                    if target_status != tk.status:
                        ApplicationService.toggle_task_status(session, tk.id, target_status)
                        st.rerun()

            with tab_delete:
                arch_label = "Unarchive Application" if app.is_archived else "Archive Application"
                if st.button(arch_label, key=f"arch_btn_{app.id}"):
                    ApplicationService.set_archived(session, app.id, not app.is_archived)
                    st.rerun()

                st.warning("Deleting an application permanently removes its status history, interviews, and linked tasks.")
                confirm_del = st.checkbox(
                    f"I confirm permanent deletion of {app.company} — {app.role}",
                    key=f"del_confirm_{app.id}",
                )
                if st.button("🗑️ Permanently Delete", key=f"del_btn_{app.id}", disabled=not confirm_del):
                    ApplicationService.delete_application(session, app.id)
                    st.success("Application deleted.")
                    st.rerun()


def _render_application_create_form(session: Session, cv_docs: dict, cl_docs: dict) -> None:
    with st.form("create_application_form", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        company = c1.text_input("Company *")
        role = c2.text_input("Role *")
        location = c3.text_input("Location", placeholder="Bucharest / Remote")

        c4, c5, c6, c7 = st.columns(4)
        work_arrangement = c4.selectbox("Arrangement", AppConfig.WORK_ARRANGEMENTS)
        employment_type = c5.selectbox("Employment Type", AppConfig.EMPLOYMENT_TYPES)
        status = c6.selectbox("Status", AppConfig.APPLICATION_STATUSES, index=0)
        priority = c7.selectbox("Priority", AppConfig.PRIORITIES, index=1)

        c8, c9, c10 = st.columns(3)
        job_url = c8.text_input("Job URL")
        source = c9.text_input("Source", placeholder="LinkedIn, Company Site, Referral")
        date_applied = c10.date_input("Date Applied (optional)", value=None)

        s1, s2, s3, s4, s5 = st.columns(5)
        salary_min = s1.number_input("Salary Min", min_value=0.0, value=0.0, step=100.0)
        salary_max = s2.number_input("Salary Max", min_value=0.0, value=0.0, step=100.0)
        currency = s3.text_input("Currency", value="EUR")
        pay_period = s4.selectbox("Pay Period", AppConfig.PAY_PERIODS, index=1)
        tax_des = s5.selectbox("Gross / Net", AppConfig.TAX_DESIGNATIONS)

        r1, r2, r3, r4 = st.columns(4)
        recruiter_name = r1.text_input("Recruiter Name")
        recruiter_contact = r2.text_input("Recruiter Contact")
        next_action = r3.text_input("Next Action")
        next_action_due = r4.date_input("Next Action Due Date", value=None)

        d1, d2 = st.columns(2)
        cv_choice = d1.selectbox("Linked CV Version", [None] + list(cv_docs.keys()), format_func=lambda x: "None" if x is None else cv_docs[x])
        cl_choice = d2.selectbox("Linked Cover Letter Version", [None] + list(cl_docs.keys()), format_func=lambda x: "None" if x is None else cl_docs[x])

        job_description = st.text_area("Full Saved Job Description", height=140)
        notes = st.text_area("Application Notes", height=80)
        allow_duplicate = st.checkbox("Save even if a similar application (company/role/URL) already exists")

        submitted = st.form_submit_button("Save Application", type="primary")
        if submitted:
            try:
                dups = ApplicationService.find_potential_duplicates(session, company, role, job_url)
                if dups and not allow_duplicate:
                    st.warning(
                        f"⚠️ Potential duplicate detected: {len(dups)} existing record(s) match this company/role or URL "
                        f"(e.g., {dups[0].company} — {dups[0].role}, Status: {dups[0].status}). "
                        "Check 'Save even if a similar application already exists' above if this is a legitimate repeat application."
                    )
                    return

                payload = ApplicationInputSchema(
                    company=company,
                    role=role,
                    location=location,
                    work_arrangement=work_arrangement,
                    employment_type=employment_type,
                    job_url=job_url,
                    source=source,
                    job_description=job_description,
                    date_applied=date_applied,
                    status=status,
                    priority=priority,
                    salary_min=salary_min if salary_min > 0 else None,
                    salary_max=salary_max if salary_max > 0 else None,
                    currency=currency,
                    pay_period=pay_period,
                    tax_designation=tax_des,
                    recruiter_name=recruiter_name,
                    recruiter_contact=recruiter_contact,
                    next_action=next_action,
                    next_action_due=next_action_due,
                    notes=notes,
                    cv_document_id=cv_choice,
                    cover_letter_document_id=cl_choice,
                )
                ApplicationService.create_application(session, payload)
                st.success(f"Saved application for {company} — {role}!")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not save application: {exc}")


def _render_application_edit_form(session: Session, app, cv_docs: dict, cl_docs: dict) -> None:
    with st.form(f"edit_application_form_{app.id}"):
        c1, c2, c3 = st.columns(3)
        company = c1.text_input("Company *", value=app.company)
        role = c2.text_input("Role *", value=app.role)
        location = c3.text_input("Location", value=app.location or "")

        c4, c5, c6, c7 = st.columns(4)
        work_arrangement = c4.selectbox(
            "Arrangement",
            AppConfig.WORK_ARRANGEMENTS,
            index=AppConfig.WORK_ARRANGEMENTS.index(app.work_arrangement)
            if app.work_arrangement in AppConfig.WORK_ARRANGEMENTS
            else 0,
        )
        employment_type = c5.selectbox(
            "Employment Type",
            AppConfig.EMPLOYMENT_TYPES,
            index=AppConfig.EMPLOYMENT_TYPES.index(app.employment_type)
            if app.employment_type in AppConfig.EMPLOYMENT_TYPES
            else 0,
        )
        status = c6.selectbox(
            "Status",
            AppConfig.APPLICATION_STATUSES,
            index=AppConfig.APPLICATION_STATUSES.index(app.status),
        )
        priority = c7.selectbox(
            "Priority",
            AppConfig.PRIORITIES,
            index=AppConfig.PRIORITIES.index(app.priority) if app.priority in AppConfig.PRIORITIES else 1,
        )

        c8, c9, c10 = st.columns(3)
        job_url = c8.text_input("Job URL", value=app.job_url or "")
        source = c9.text_input("Source", value=app.source or "")
        date_applied = c10.date_input("Date Applied", value=app.date_applied)

        s1, s2, s3, s4, s5 = st.columns(5)
        salary_min = s1.number_input("Salary Min", min_value=0.0, value=float(app.salary_min or 0.0), step=100.0)
        salary_max = s2.number_input("Salary Max", min_value=0.0, value=float(app.salary_max or 0.0), step=100.0)
        currency = s3.text_input("Currency", value=app.currency or "EUR")
        pay_period = s4.selectbox(
            "Pay Period",
            AppConfig.PAY_PERIODS,
            index=AppConfig.PAY_PERIODS.index(app.pay_period) if app.pay_period in AppConfig.PAY_PERIODS else 1,
        )
        tax_des = s5.selectbox(
            "Gross / Net",
            AppConfig.TAX_DESIGNATIONS,
            index=AppConfig.TAX_DESIGNATIONS.index(app.tax_designation)
            if app.tax_designation in AppConfig.TAX_DESIGNATIONS
            else 2,
        )

        r1, r2, r3, r4 = st.columns(4)
        recruiter_name = r1.text_input("Recruiter Name", value=app.recruiter_name or "")
        recruiter_contact = r2.text_input("Recruiter Contact", value=app.recruiter_contact or "")
        next_action = r3.text_input("Next Action", value=app.next_action or "")
        next_action_due = r4.date_input("Next Action Due", value=app.next_action_due)

        cv_options = [None] + list(cv_docs.keys())
        cl_options = [None] + list(cl_docs.keys())
        d1, d2 = st.columns(2)
        cv_choice = d1.selectbox(
            "Linked CV",
            cv_options,
            index=cv_options.index(app.cv_document_id) if app.cv_document_id in cv_options else 0,
            format_func=lambda x: "None" if x is None else cv_docs[x],
        )
        cl_choice = d2.selectbox(
            "Linked Cover Letter",
            cl_options,
            index=cl_options.index(app.cover_letter_document_id)
            if app.cover_letter_document_id in cl_options
            else 0,
            format_func=lambda x: "None" if x is None else cl_docs[x],
        )

        job_description = st.text_area("Job Description", value=app.job_description or "", height=120)
        notes = st.text_area("Notes", value=app.notes or "", height=80)
        status_note = st.text_input("Status Transition Note (logged if status changes)")

        if st.form_submit_button("Update Application"):
            try:
                payload = ApplicationInputSchema(
                    company=company,
                    role=role,
                    location=location,
                    work_arrangement=work_arrangement,
                    employment_type=employment_type,
                    job_url=job_url,
                    source=source,
                    job_description=job_description,
                    date_applied=date_applied,
                    status=status,
                    priority=priority,
                    salary_min=salary_min if salary_min > 0 else None,
                    salary_max=salary_max if salary_max > 0 else None,
                    currency=currency,
                    pay_period=pay_period,
                    tax_designation=tax_des,
                    recruiter_name=recruiter_name,
                    recruiter_contact=recruiter_contact,
                    next_action=next_action,
                    next_action_due=next_action_due,
                    notes=notes,
                    cv_document_id=cv_choice,
                    cover_letter_document_id=cl_choice,
                )
                ApplicationService.update_application(session, app.id, payload, status_note=status_note or None)
                st.success("Application updated without duplicating records.")
                st.rerun()
            except Exception as exc:
                st.error(f"Update failed: {exc}")