import datetime
from typing import Literal
from pydantic import BaseModel, Field

# Opportunity types
OpportunityType = Literal["application", "lead"]

# Stage / Status progression
OpportunityStage = Literal[
    "lead",
    "applied",
    "screening",
    "interviewing",
    "assessment",
    "offer",
    "rejected",
    "withdrawn",
]

# Event types
EventType = Literal[
    "application_submitted",
    "recruiter_outreach",
    "screening_invitation",
    "screening_scheduled",
    "technical_assessment_assigned",
    "technical_assessment_submitted",
    "interview_scheduled",
    "interview_completed",
    "rejection_received",
    "offer_received",
    "offer_accepted",
    "offer_declined",
    "general_update",
]


class ExtractedContact(BaseModel):
    """Recruiter, hiring manager, or referral contact extracted from email."""

    name: str = Field(..., description="Full name of the contact")
    email: str = Field(..., description="Email address of the contact")
    role: str | None = Field(default=None, description="e.g. recruiter, hiring_manager, interviewer")
    linkedin_url: str | None = Field(default=None, description="LinkedIn profile URL if mentioned")


class ExtractedMilestone(BaseModel):
    """Interview date, technical assessment deadline, or offer response deadline."""

    title: str = Field(..., description="Title of the milestone (e.g. System Design Interview)")
    milestone_type: Literal["interview", "technical_assessment", "deadline", "offer_response"]
    scheduled_at: datetime.datetime | None = Field(
        default=None,
        description="Exact ISO timestamp if date and time are both known",
    )
    scheduled_date: datetime.date | None = Field(
        default=None,
        description="Date-only if time of day was not specified",
    )
    is_time_uncertain: bool = Field(
        default=False,
        description="True if exact time is ambiguous or pending confirmation",
    )


class ExtractedFollowUp(BaseModel):
    """Actionable recommendation or follow-up item."""

    title: str = Field(..., description="What the candidate needs to do (e.g. Reply with availability)")
    description: str | None = Field(default=None, description="Detailed instructions or context")
    due_date: datetime.date = Field(..., description="Target completion date")


class EmailExtractionResult(BaseModel):
    """
    Standardized structured outcome produced by the AI extraction pipeline:
    - Identifies if the email is career-related.
    - Proposes company, role, stage, contacts, milestones, and follow-ups.
    - Includes confidence score and source quote evidence.
    """

    is_career_related: bool = Field(
        ...,
        description="True if this email is an application, recruiter outreach, interview, offer, or rejection",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score of the extraction (0.0 to 1.0)",
    )

    # Opportunity details (if career related)
    company_name: str | None = Field(default=None, description="Normalized company name, e.g. Stripe, Google")
    company_domain: str | None = Field(default=None, description="Company web domain if detectable, e.g. stripe.com")
    role_title: str | None = Field(default=None, description="Job title, e.g. Staff Backend Engineer")
    opportunity_type: OpportunityType = Field(default="application")
    current_stage: OpportunityStage | None = Field(default=None)

    # Event details
    event_type: EventType | None = Field(default=None)
    event_summary: str | None = Field(default=None, description="One-line factual summary of this communication")
    evidence_quote: str | None = Field(
        default=None,
        description="Exact excerpt from the email body supporting this classification",
    )

    # Associated entities
    salary_text: str | None = Field(default=None, description="Salary/compensation mentioned, if any")
    location: str | None = Field(default=None, description="Job location or Remote, if mentioned")
    contacts: list[ExtractedContact] = Field(default_factory=list)
    milestones: list[ExtractedMilestone] = Field(default_factory=list)
    follow_ups: list[ExtractedFollowUp] = Field(default_factory=list)

    # Flag for human review
    requires_human_review: bool = Field(
        default=False,
        description="True if the match, role title, or status transition is ambiguous or low confidence",
    )
    review_reason: str | None = Field(
        default=None,
        description="Explanation why human review is recommended",
    )
