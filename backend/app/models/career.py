import datetime
import uuid
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class Company(Base, TimestampMixin):
    """Normalized company record."""

    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    opportunities: Mapped[list["Opportunity"]] = relationship("Opportunity", back_populates="company")
    contacts: Mapped[list["Contact"]] = relationship("Contact", back_populates="company")


class Contact(Base, TimestampMixin):
    """Recruiter, hiring manager, or referral contact."""

    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    role: Mapped[str | None] = mapped_column(String(128), nullable=True)  # recruiter, hiring_manager, referral
    linkedin_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    company: Mapped["Company | None"] = relationship("Company", back_populates="contacts")
    opportunities: Mapped[list["OpportunityContact"]] = relationship("OpportunityContact", back_populates="contact")


class Opportunity(Base, TimestampMixin):
    """Job application or inbound recruiter lead pipeline item."""

    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    role_title: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # application vs lead
    opportunity_type: Mapped[str] = mapped_column(
        String(32),
        default="application",
        nullable=False,
    )  # application, lead

    # Status state machine
    status: Mapped[str] = mapped_column(
        String(32),
        default="applied",
        nullable=False,
        index=True,
    )  # lead, applied, screening, interviewing, assessment, offer, rejected, withdrawn

    # Provenance
    provenance: Mapped[str] = mapped_column(
        String(32),
        default="inferred",
        nullable=False,
    )  # confirmed, inferred, manual

    # Optimistic concurrency lock
    record_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    salary_text: Mapped[str | None] = mapped_column(String(128), nullable=True)
    location: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="opportunities")
    events: Mapped[list["OpportunityEvent"]] = relationship(
        "OpportunityEvent",
        back_populates="opportunity",
        cascade="all, delete-orphan",
        order_by="OpportunityEvent.occurred_at.asc()",
    )
    milestones: Mapped[list["Milestone"]] = relationship(
        "Milestone",
        back_populates="opportunity",
        cascade="all, delete-orphan",
    )
    follow_ups: Mapped[list["FollowUpTask"]] = relationship(
        "FollowUpTask",
        back_populates="opportunity",
        cascade="all, delete-orphan",
    )
    contacts: Mapped[list["OpportunityContact"]] = relationship(
        "OpportunityContact",
        back_populates="opportunity",
        cascade="all, delete-orphan",
    )


class OpportunityContact(Base):
    """Many-to-many junction table between opportunities and contacts."""

    __tablename__ = "opportunity_contacts"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        primary_key=True,
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        primary_key=True,
    )

    opportunity: Mapped["Opportunity"] = relationship("Opportunity", back_populates="contacts")
    contact: Mapped["Contact"] = relationship("Contact", back_populates="opportunities")


class OpportunityEvent(Base, TimestampMixin):
    """Chronological timeline event linked to source email evidence."""

    __tablename__ = "opportunity_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("email_messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )  # application_submitted, recruiter_outreach, screening_invitation, interview_scheduled, rejection_received, offer_received, etc.
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # Provenance
    provenance: Mapped[str] = mapped_column(String(32), default="inferred", nullable=False)

    opportunity: Mapped["Opportunity"] = relationship("Opportunity", back_populates="events")
    email_message: Mapped["EmailMessage | None"] = relationship("EmailMessage")


class Milestone(Base, TimestampMixin):
    """Interview, assessment deadline, or offer response deadline."""

    __tablename__ = "milestones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    milestone_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )  # interview, technical_assessment, deadline, offer_response
    
    # Timezone-aware timestamp OR date-only if time is not specified
    scheduled_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    is_time_uncertain: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
    )  # pending, completed, cancelled, missed

    opportunity: Mapped["Opportunity"] = relationship("Opportunity", back_populates="milestones")


class FollowUpTask(Base, TimestampMixin):
    """Actionable recommendation or follow-up item."""

    __tablename__ = "follow_up_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)

    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
        index=True,
    )  # pending, completed, dismissed

    opportunity: Mapped["Opportunity"] = relationship("Opportunity", back_populates="follow_ups")


class ReviewProposal(Base, TimestampMixin):
    """Human-in-the-loop review item for ambiguous classifications or matches."""

    __tablename__ = "review_proposals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("email_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="SET NULL"),
        nullable=True,
    )
    proposal_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )  # ambiguous_opportunity_match, ambiguous_status_change, low_confidence_extraction
    
    proposed_changes: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
        index=True,
    )  # pending, accepted, edited, dismissed
    
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
