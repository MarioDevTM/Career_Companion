from datetime import date
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator, model_validator

from src.config import AppConfig


class ApplicationInputSchema(BaseModel):
    company: str = Field(..., min_length=1, max_length=200)
    role: str = Field(..., min_length=1, max_length=200)
    location: Optional[str] = Field(default=None, max_length=200)
    work_arrangement: str = Field(default="Unspecified")
    employment_type: str = Field(default="Full-time")
    job_url: Optional[str] = Field(default=None, max_length=500)
    source: Optional[str] = Field(default=None, max_length=100)
    job_description: Optional[str] = Field(default=None)
    date_applied: Optional[date] = Field(default=None)
    status: str = Field(default="Saved")
    priority: str = Field(default="Medium")
    salary_min: Optional[float] = Field(default=None, ge=0)
    salary_max: Optional[float] = Field(default=None, ge=0)
    currency: Optional[str] = Field(default="EUR", max_length=10)
    pay_period: Optional[str] = Field(default="Monthly")
    tax_designation: Optional[str] = Field(default="Unspecified")
    recruiter_name: Optional[str] = Field(default=None, max_length=200)
    recruiter_contact: Optional[str] = Field(default=None, max_length=255)
    next_action: Optional[str] = Field(default=None, max_length=255)
    next_action_due: Optional[date] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    cv_document_id: Optional[int] = Field(default=None)
    cover_letter_document_id: Optional[int] = Field(default=None)

    @field_validator("company", "role")
    @classmethod
    def strip_required_text(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty or whitespace only.")
        return cleaned

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in AppConfig.APPLICATION_STATUSES:
            raise ValueError(f"Unsupported application status: {v}")
        return v

    @model_validator(mode="after")
    def check_salary_bounds(self):
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_min > self.salary_max:
                raise ValueError("Minimum salary cannot exceed maximum salary.")
        return self


class ExtractedSkillRequirement(BaseModel):
    skill_name: str = Field(..., description="Specific technical or domain skill name.")
    requirement_level: Literal["Required", "Preferred"] = Field(
        ..., description="Whether the job description marks this skill as required or preferred."
    )
    source_type: Literal["Explicit", "Inferred"] = Field(
        ..., description="Explicit if stated directly in the job text, Inferred if deduced by AI."
    )
    source_quote_or_reason: str = Field(
        ..., description="Direct quote from the job description, or explanation if inferred."
    )
    profile_evidence_status: Literal["Supported", "Partial", "Missing / Unknown"] = Field(
        ..., description="How well the user's supplied profile/documents demonstrate this skill."
    )
    profile_evidence_detail: str = Field(
        ..., description="Cite specific evidence from supplied profile/CV, or state Unknown if not found."
    )


class ProposedTaskItem(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(default="")
    task_type: Literal["Application", "Interview Prep", "Study"] = Field(default="Study")
    suggested_due_days: Optional[int] = Field(default=3, ge=0, le=365)


class JobAnalysisOutput(BaseModel):
    role_summary: str = Field(..., description="Concise summary of the role based strictly on the job description.")
    explicit_requirements: List[str] = Field(
        default_factory=list, description="Requirements explicitly stated in the source text."
    )
    ai_inferences: List[str] = Field(
        default_factory=list, description="Reasonable inferences clearly separated from explicit source statements."
    )
    skill_breakdown: List[ExtractedSkillRequirement] = Field(default_factory=list)
    unknowns_and_gaps: List[str] = Field(
        default_factory=list,
        description="Facts, compensation details, or experience areas that are unknown or unverified in the supplied materials.",
    )
    proposed_tasks: List[ProposedTaskItem] = Field(
        default_factory=list,
        description="Suggested preparation or follow-up tasks the user can review and optionally save.",
    )


class GeneratedQuizQuestionSchema(BaseModel):
    question_text: str = Field(..., min_length=5)
    options: List[str] = Field(..., min_length=4, max_length=4, description="Exactly 4 answer choices.")
    correct_option_index: int = Field(..., ge=0, le=3, description="Zero-based index (0 to 3) of the correct option.")
    explanation: str = Field(..., min_length=5, description="Detailed explanation of why the correct option is right.")
    source_citation: Optional[str] = Field(
        default=None, description="Document name and page reference if derived from supplied material."
    )
    suggested_revisit_topic: str = Field(..., description="Specific sub-topic to review if the user misses this question.")


class QuizGenerationOutput(BaseModel):
    topic_summary: str
    questions: List[GeneratedQuizQuestionSchema] = Field(..., min_length=1, max_length=10)
    unsupported_material_notice: Optional[str] = Field(
        default=None,
        description="Note if any part of the requested topic was not covered by the supplied study notes/documents.",
    )


class StudyPlanMilestone(BaseModel):
    day_or_week_label: str = Field(..., description="e.g., Day 1-2 or Week 1")
    focus_topic: str
    activities: List[str]
    estimated_minutes: int = Field(..., ge=10, le=600)


class StudyPlanOutput(BaseModel):
    plan_title: str
    rationale: str = Field(..., description="How deadlines, available time, and past practice performance shaped this plan.")
    milestones: List[StudyPlanMilestone] = Field(..., min_length=1)
    proposed_tasks: List[ProposedTaskItem] = Field(default_factory=list)


class AnswerCoachOutput(BaseModel):
    critique_strengths: List[str]
    critique_gaps: List[str]
    improved_draft: str = Field(
        ...,
        description="Refined answer using ONLY facts present in the user's draft and experience bank.",
    )
    unverified_placeholders_needed: List[str] = Field(
        default_factory=list,
        description="Specific questions asking the user for real metrics or tools they actually used, instead of inventing them.",
    )