import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import AppConfig
from src.models import ProfileEntry


def render_experience_view(session: Session) -> None:
    st.title("Experience Bank")
    st.caption(
        "Store real projects, achievements, technical skills with evidence, work/volunteering experiences, "
        "and STAR behavioral stories so the AI Assistant can ground interview preparation without inventing facts."
    )

    with st.expander("Add Entry to Experience Bank", expanded=False):
        with st.form("add_experience_entry_form"):
            c1, c2, c3 = st.columns(3)
            category = c1.selectbox(
                "Category *",
                ["STAR Story", "Project / Achievement", "Technical Skill", "Work / Volunteering / Leadership"],
            )
            title = c2.text_input("Title / Headline *", placeholder="e.g., Migrated Monolith Auth to OAuth2")
            organization = c3.text_input("Organization / Context", placeholder="e.g., Acme Corp / Open Source")

            c4, c5 = st.columns(2)
            role_or_skill = c4.text_input("Role or Primary Skill")
            date_range = c5.text_input("Date Range", placeholder="2024 - Present")

            description = st.text_area("Summary / Responsibilities", height=70)
            evidence = st.text_area("Supporting Evidence & Concrete Metrics", height=65)

            st.markdown("**STAR Behavioral Fields (Optional — recommended for STAR Stories)**")
            s1, s2 = st.columns(2)
            situation = s1.text_area("Situation", height=65)
            task = s2.text_area("Task", height=65)
            s3, s4 = st.columns(2)
            action = s3.text_area("Action", height=65)
            result = s4.text_area("Result (Actual verified outcome)", height=65)

            tags = st.multiselect("Competency Tags", AppConfig.COMPETENCY_TAGS)

            if st.form_submit_button("Save Experience Entry", type="primary"):
                if title.strip():
                    entry = ProfileEntry(
                        category=category,
                        title=title.strip(),
                        organization=organization.strip() or None,
                        role_or_skill=role_or_skill.strip() or None,
                        date_range=date_range.strip() or None,
                        description=description.strip() or None,
                        evidence=evidence.strip() or None,
                        situation=situation.strip() or None,
                        task=task.strip() or None,
                        action=action.strip() or None,
                        result=result.strip() or None,
                        competency_tags=",".join(tags) if tags else None,
                    )
                    session.add(entry)
                    session.commit()
                    st.success("Experience entry saved!")
                    st.rerun()

    filter_col1, filter_col2 = st.columns(2)
    cat_filter = filter_col1.selectbox(
        "Filter by Category",
        ["All", "STAR Story", "Project / Achievement", "Technical Skill", "Work / Volunteering / Leadership"],
    )
    tag_filter = filter_col2.selectbox("Filter by Competency Tag", ["All"] + AppConfig.COMPETENCY_TAGS)

    entries = list(session.scalars(select(ProfileEntry).order_by(ProfileEntry.created_at.desc())).all())
    if cat_filter != "All":
        entries = [e for e in entries if e.category == cat_filter]
    if tag_filter != "All":
        entries = [e for e in entries if tag_filter in (e.competency_tags or "").split(",")]

    if not entries:
        st.info("No experience entries match the selected filters.")
        return

    for entry in entries:
        with st.container(border=True):
            st.subheader(f"[{entry.category}] {entry.title}")
            st.caption(
                f"Organization: {entry.organization or '—'} | Role/Skill: {entry.role_or_skill or '—'} | Dates: {entry.date_range or '—'}"
            )
            if entry.competency_tags:
                st.markdown(" ".join(f"`#{t}`" for t in entry.competency_tags.split(",") if t))
            if entry.description:
                st.write(entry.description)
            if entry.evidence:
                st.markdown(f"**Supporting Evidence:** {entry.evidence}")
            if any([entry.situation, entry.task, entry.action, entry.result]):
                st.markdown(
                    f"- **Situation:** {entry.situation or '—'}\n"
                    f"- **Task:** {entry.task or '—'}\n"
                    f"- **Action:** {entry.action or '—'}\n"
                    f"- **Result:** {entry.result or '—'}"
                )
            if st.button("Delete Entry", key=f"del_exp_{entry.id}"):
                session.delete(entry)
                session.commit()
                st.rerun()
