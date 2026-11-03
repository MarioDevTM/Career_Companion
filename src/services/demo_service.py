from datetime import date, datetime, timedelta, timezone
from sqlalchemy.orm import Session

from src.models import ProfileEntry
from src.schemas import ApplicationInputSchema
from src.services.application_service import ApplicationService
from src.services.learning_service import LearningService


class DemoService:
    @staticmethod
    def load_fictional_demo_data(session: Session) -> None:
        today = date.today()
        now_utc = datetime.now(timezone.utc)

        app1 = ApplicationService.create_application(
            session,
            ApplicationInputSchema(
                company="Danube Cloud Systems",
                role="Senior Python Backend Engineer",
                location="Bucharest, Romania",
                work_arrangement="Hybrid",
                employment_type="Full-time",
                job_url="https://example.com/jobs/danube-senior-python",
                source="Company Careers Page",
                job_description=(
                    "We are looking for a Senior Python Backend Engineer in Bucharest.\n"
                    "Required Skills: Python 3.11+, SQLAlchemy, FastAPI, PostgreSQL, pytest, Docker.\n"
                    "Preferred Skills: Kubernetes, AWS Certified Developer, Redis caching.\n"
                    "Responsibilities: Design resilient APIs, mentor engineers, and optimize SQL queries."
                ),
                date_applied=today - timedelta(days=10),
                status="Applied",
                priority="High",
                salary_min=4200,
                salary_max=5200,
                currency="EUR",
                pay_period="Monthly",
                tax_designation="Net",
                recruiter_name="Elena Ionescu",
                recruiter_contact="elena.ionescu@example.com",
                next_action="Prepare system design architecture notes",
                next_action_due=today + timedelta(days=1),
                notes="Referral from former colleague.",
            ),
            status_note="Submitted application with tailored backend CV.",
        )

        ApplicationService.update_application(
            session,
            app1.id,
            ApplicationInputSchema(
                company=app1.company,
                role=app1.role,
                location=app1.location,
                work_arrangement=app1.work_arrangement,
                employment_type=app1.employment_type,
                job_url=app1.job_url,
                source=app1.source,
                job_description=app1.job_description,
                date_applied=app1.date_applied,
                status="Interview",
                priority=app1.priority,
                salary_min=app1.salary_min,
                salary_max=app1.salary_max,
                currency=app1.currency,
                pay_period=app1.pay_period,
                tax_designation=app1.tax_designation,
                recruiter_name=app1.recruiter_name,
                recruiter_contact=app1.recruiter_contact,
                next_action=app1.next_action,
                next_action_due=app1.next_action_due,
                notes=app1.notes,
            ),
            status_note="Passed initial screening call; technical interview scheduled.",
        )

        app2 = ApplicationService.create_application(
            session,
            ApplicationInputSchema(
                company="Carpathian FinTech Lab",
                role="Platform Data Engineer",
                location="Cluj-Napoca / Remote",
                work_arrangement="Remote",
                employment_type="Full-time",
                job_url="https://example.com/jobs/carpathian-data",
                source="LinkedIn",
                job_description=(
                    "Seeking a Platform Data Engineer to build streaming ETL pipelines.\n"
                    "Required: Python, SQL, Apache Kafka, Data Modeling.\n"
                    "Preferred: dbt, Snowflake."
                ),
                date_applied=None,
                status="Saved",
                priority="Medium",
                salary_min=85000,
                salary_max=105000,
                currency="EUR",
                pay_period="Yearly",
                tax_designation="Gross",
                next_action="Tailor CV for streaming pipelines before applying",
                next_action_due=today,
            ),
            status_note="Saved role for review.",
        )

        interview = ApplicationService.create_interview(
            session=session,
            application_id=app1.id,
            scheduled_at=now_utc + timedelta(days=2, hours=3),
            format_str="Video Call",
            stage="Technical & Architecture Deep Dive",
            participants="Andrei Popa (Staff Engineer), Elena Ionescu (Recruiter)",
            checklist_items=[
                {"item": "Review SQLAlchemy 2.0 async session lifecycle", "done": True},
                {"item": "Prepare STAR story on database latency incident", "done": False},
            ],
            questions_to_ask="How does the team handle database schema migrations during zero-downtime deploys?",
        )

        ApplicationService.add_interview_question(
            session,
            interview_id=interview.id,
            category="Technical",
            origin="ai_practice",
            question_text="Explain how SQLAlchemy's unit-of-work pattern tracks dirty objects before flush.",
            answer_notes="Mention identity map, attribute instrumentation, and explicit flush vs commit.",
        )
        ApplicationService.add_interview_question(
            session,
            interview_id=interview.id,
            category="Behavioral",
            origin="confirmed_asked",
            question_text="Tell me about a time you resolved a production bottleneck under tight deadlines.",
            answer_notes="Used the payment webhook indexing story from Experience Bank.",
        )

        skill_sa, _ = ApplicationService.link_skill_to_application(
            session,
            app1.id,
            "SQLAlchemy & Database Architecture",
            category="Backend",
            requirement_level="Required",
            source_type="Explicit",
            evidence_snippet="Required Skills: Python 3.11+, SQLAlchemy, FastAPI, PostgreSQL",
        )
        skill_k8s, _ = ApplicationService.link_skill_to_application(
            session,
            app1.id,
            "Kubernetes & Container Orchestration",
            category="DevOps",
            requirement_level="Preferred",
            source_type="Explicit",
            evidence_snippet="Preferred Skills: Kubernetes, AWS Certified Developer",
        )
        skill_aws = LearningService.create_or_update_skill(
            session, "AWS Certified Developer Associate (DVA-C02)", category="Certification", self_confidence=3
        )

        goal_job = LearningService.create_learning_goal(
            session,
            title="Master SQLAlchemy 2.0 & High-Concurrency APIs",
            goal_type="Job Preparation",
            description="Deepen ORM optimization and transaction isolation knowledge for backend roles.",
            target_date=today + timedelta(days=14),
            application_ids=[app1.id, app2.id],
        )
        goal_cert = LearningService.create_learning_goal(
            session,
            title="Pass AWS Certified Developer Associate Exam",
            goal_type="Certification",
            description="Independent certification goal covering IAM, Lambda, DynamoDB, and KMS.",
            target_date=today + timedelta(days=45),
            application_ids=[],
        )

        LearningService.log_study_session(
            session,
            duration_minutes=75,
            activity_type="Documentation & Hands-on Coding",
            notes="Practiced selectinload vs joinedload query plans.",
            learning_goal_id=goal_job.id,
            skill_id=skill_sa.id,
        )
        LearningService.log_study_session(
            session,
            duration_minutes=45,
            activity_type="Certification Study",
            notes="Reviewed DynamoDB partition key design and GSI throttling.",
            learning_goal_id=goal_cert.id,
            skill_id=skill_aws.id,
        )

        q1 = LearningService.create_quiz_question(
            session,
            question_text="Which SQLAlchemy relationship loading strategy emits a second SELECT with an IN clause to avoid Cartesian products on one-to-many collections?",
            options=["joinedload", "selectinload", "lazyload", "raiseload"],
            correct_option_index=1,
            explanation="selectinload emits a secondary SELECT using WHERE parent_id IN (...) which prevents row duplication across large collections.",
            skill_id=skill_sa.id,
            learning_goal_id=goal_job.id,
            source_citation="SQLAlchemy 2.0 ORM Documentation",
            suggested_revisit_topic="Relationship Loading Techniques",
        )
        LearningService.record_quiz_attempt(session, q1.id, 1)

        LearningService.create_revision_item(
            session,
            prompt_front="When should you prefer selectinload over joinedload in SQLAlchemy?",
            answer_back="Prefer selectinload for one-to-many or many-to-many collections to avoid Cartesian product amplification; prefer joinedload for many-to-one references.",
            skill_id=skill_sa.id,
            learning_goal_id=goal_job.id,
            initial_review_date=today,
        )
        LearningService.create_revision_item(
            session,
            prompt_front="What is the maximum item size in Amazon DynamoDB?",
            answer_back="400 KB, including both attribute names and attribute values.",
            skill_id=skill_aws.id,
            learning_goal_id=goal_cert.id,
            initial_review_date=today,
        )

        ApplicationService.create_task(
            session,
            title="Complete mock interview session for Danube Cloud Systems",
            task_type="Interview Prep",
            due_date=today,
            priority="High",
            application_id=app1.id,
            learning_goal_id=goal_job.id,
            skill_id=skill_sa.id,
        )
        ApplicationService.create_task(
            session,
            title="Practice 20 IAM policy evaluation flashcards",
            task_type="Study",
            due_date=today,
            priority="Medium",
            learning_goal_id=goal_cert.id,
            skill_id=skill_aws.id,
        )

        session.add_all(
            [
                ProfileEntry(
                    category="STAR Story",
                    title="Reduced Payment Webhook Processing Latency by 68%",
                    organization="BlackSea Payments SRL",
                    role_or_skill="Backend Engineer",
                    date_range="2024 - 2026",
                    situation="Merchant webhook deliveries were timing out during flash sales with p95 latency exceeding 4.2 seconds.",
                    task="Identify the database contention bottleneck and bring p95 latency under 1.5 seconds without dropping events.",
                    action="Profiled SQL queries, replaced N+1 ORM lookups with batched selectinload queries, and added a composite partial index on pending events.",
                    result="Cut p95 webhook processing latency from 4.2s to 1.3s (-68%) and eliminated queue backlog alerts.",
                    evidence="Production Grafana dashboard metrics and post-incident engineering review.",
                    competency_tags="troubleshooting,ownership,system-design,prioritization",
                ),
                ProfileEntry(
                    category="Technical Skill",
                    title="Python & SQLAlchemy Backend Engineering",
                    organization="BlackSea Payments SRL",
                    role_or_skill="Python 3.12, SQLAlchemy 2.0, FastAPI, pytest",
                    date_range="2022 - 2026",
                    description="Built and maintained multi-service transactional APIs and automated pytest suites.",
                    evidence="4 years production delivery across billing and settlement services.",
                    competency_tags="system-design,troubleshooting,teamwork",
                ),
            ]
        )
        session.commit()