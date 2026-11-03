import plotly.express as px
import pandas as pd
import streamlit as st
from sqlalchemy.orm import Session

from src.services.insights_service import InsightsService


def render_insights_view(session: Session) -> None:
    st.title("Insights & Progress Analytics")
    st.caption(
        "Conversion metrics exclude saved-but-unapplied roles from denominators and use full status history "
        "to determine whether an application ever reached an interview. AI fit assessments are never shown as hiring probabilities."
    )

    app_metrics = InsightsService.compute_application_metrics(session)
    learn_metrics = InsightsService.compute_learning_metrics(session)

    if app_metrics["small_sample_warning"]:
        st.warning(
            f" **Small Sample Notice:** You currently have **{app_metrics['submitted_applications_denominator']}** "
            "submitted application(s) (excluding saved-only roles). Conversion percentages require a larger sample size for meaningful conclusions."
        )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "Submitted Applications",
        app_metrics["submitted_applications_denominator"],
        help=f"Excludes {app_metrics['saved_unapplied_count']} Saved-only role(s).",
    )
    m2.metric(
        "Employer Response Rate",
        f"{app_metrics['response_rate_pct']}%",
        help=f"{app_metrics['ever_responded_count']} / {app_metrics['submitted_applications_denominator']} submitted applications recorded an employer response.",
    )
    m3.metric(
        "Reached Interview Stage",
        f"{app_metrics['interview_conversion_pct']}%",
        help=f"{app_metrics['ever_interviewed_count']} / {app_metrics['submitted_applications_denominator']} submitted applications ever reached Interview/Offer in status history.",
    )
    m4.metric(
        "Reached Offer Stage",
        f"{app_metrics['offer_conversion_pct']}%",
        help=f"{app_metrics['ever_offered_count']} / {app_metrics['submitted_applications_denominator']} submitted applications ever reached Offer/Accepted.",
    )

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Current Status Distribution")
        status_dist = app_metrics["status_distribution"]
        if status_dist:
            df_status = pd.DataFrame(
                [{"Status": k, "Count": v} for k, v in status_dist.items()]
            )
            fig_status = px.bar(df_status, x="Status", y="Count", color="Status")
            st.plotly_chart(fig_status, width="stretch")
        else:
            st.caption("No application data available.")

        st.subheader("Applications by Source")
        source_dist = app_metrics["source_distribution"]
        if source_dist:
            df_source = pd.DataFrame(
                [{"Source": k, "Count": v} for k, v in source_dist.items()]
            )
            fig_source = px.pie(df_source, names="Source", values="Count", hole=0.4)
            st.plotly_chart(fig_source, width="stretch")

    with col2:
        st.subheader("Applications Over Time")
        t_df = app_metrics["timeline_df"]
        if not t_df.empty:
            grouped = t_df.groupby("date").size().reset_index(name="Applications")
            fig_time = px.line(grouped, x="date", y="Applications", markers=True)
            st.plotly_chart(fig_time, width="stretch")
        else:
            st.caption("No dated applications to plot.")

        st.subheader("Frequently Requested Skills Across Analyzed Jobs")
        top_skills = app_metrics["top_requested_skills"]
        if top_skills:
            df_skills = pd.DataFrame(top_skills, columns=["Skill", "Job Count"])
            fig_skills = px.bar(df_skills, x="Job Count", y="Skill", orientation="h")
            st.plotly_chart(fig_skills, width="stretch")
        else:
            st.caption("No skills linked to applications yet.")

    st.divider()
    l_col1, l_col2 = st.columns(2)
    with l_col1:
        st.subheader(f"Study Activity ({learn_metrics['total_study_minutes']} total mins)")
        s_df = learn_metrics["study_df"]
        if not s_df.empty:
            fig_study = px.bar(s_df, x="date", y="minutes", color="skill", title="Study Minutes by Date & Skill")
            st.plotly_chart(fig_study, width="stretch")
        else:
            st.caption("No study sessions logged yet.")

    with l_col2:
        st.subheader(f"Topic-Level Quiz Results ({learn_metrics['total_quiz_attempts']} attempts)")
        q_df = learn_metrics["quiz_df"]
        if not q_df.empty:
            fig_quiz = px.bar(
                q_df,
                x="skill",
                y="accuracy_pct",
                hover_data=["attempts"],
                range_y=[0, 100],
                title="Quiz Accuracy (%) by Skill",
            )
            st.plotly_chart(fig_quiz, width="stretch")
        else:
            st.caption("No quiz attempts recorded yet.")
