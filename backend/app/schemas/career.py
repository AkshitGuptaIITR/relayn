import datetime
import uuid
from pydantic import BaseModel


class ContactDTO(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: str | None = None
    linkedin_url: str | None = None


class MilestoneDTO(BaseModel):
    id: uuid.UUID
    title: str
    milestone_type: str
    round_category: str | None = None
    round_number: int | None = None
    meeting_url: str | None = None
    prep_notes: str | None = None
    scheduled_at: datetime.datetime | None = None
    scheduled_date: datetime.date | None = None
    is_time_uncertain: bool = False
    status: str


class FollowUpTaskDTO(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    due_date: datetime.date
    status: str


class OpportunityEventDTO(BaseModel):
    id: uuid.UUID
    event_type: str
    summary: str
    occurred_at: datetime.datetime
    email_message_id: uuid.UUID | None = None


class OpportunitySummaryDTO(BaseModel):
    id: uuid.UUID
    company_name: str
    company_domain: str | None = None
    role_title: str
    opportunity_type: str
    status: str
    salary_text: str | None = None
    location: str | None = None
    last_activity_at: datetime.datetime
    pending_follow_ups_count: int = 0
    upcoming_interviews_count: int = 0


class OpportunityDetailDTO(BaseModel):
    id: uuid.UUID
    company_name: str
    company_domain: str | None = None
    role_title: str
    opportunity_type: str
    status: str
    salary_text: str | None = None
    location: str | None = None
    notes: str | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    
    contacts: list[ContactDTO] = []
    milestones: list[MilestoneDTO] = []
    follow_ups: list[FollowUpTaskDTO] = []
    events: list[OpportunityEventDTO] = []


class ReviewProposalDTO(BaseModel):
    id: uuid.UUID
    email_message_id: uuid.UUID
    opportunity_id: uuid.UUID | None = None
    proposal_type: str
    proposed_changes: dict
    status: str
    created_at: datetime.datetime
