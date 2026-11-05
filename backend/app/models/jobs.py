import datetime
import uuid
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class Job(Base, TimestampMixin):
    """PostgreSQL-backed durable job queue for worker tasks."""

    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )  # sync_mailbox, process_email, refresh_follow_ups, purge_mailbox
    
    unique_key: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )  # Idempotency / deduplication key

    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    
    # State
    status: Mapped[str] = mapped_column(
        String(32),
        default="queued",
        nullable=False,
        index=True,
    )  # queued, running, completed, failed, cancelled

    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    
    # Leases and Heartbeats for concurrent workers
    lease_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    leased_until: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    
    # Error diagnostics
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Generation check to immediately cancel stale jobs when mailbox is purged/disconnected
    generation: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
