import datetime
import uuid
from sqlalchemy import (
    BigInteger,
    Boolean,
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


class MailboxAccount(Base, TimestampMixin):
    """Connected Gmail mailbox singleton."""

    __tablename__ = "mailbox_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_address: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    # Encrypted refresh token and access token
    encrypted_credentials: Mapped[str | None] = mapped_column(Text, nullable=True)
    scopes: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    # Sync state
    sync_status: Mapped[str] = mapped_column(
        String(32),
        default="idle",
        nullable=False,
    )  # idle, syncing, error, disconnected
    last_history_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_synced_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Generation counter: incremented on disconnect/purge to fence out in-flight jobs
    generation: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    messages: Mapped[list["EmailMessage"]] = relationship(
        "EmailMessage",
        back_populates="mailbox",
        cascade="all, delete-orphan",
    )


class EmailMessage(Base, TimestampMixin):
    """Imported raw email message metadata and sanitized plain text body."""

    __tablename__ = "email_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mailbox_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mailbox_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gmail_message_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    gmail_thread_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    history_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    sender: Mapped[str] = mapped_column(String(255), nullable=False)
    recipients: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    subject: Mapped[str] = mapped_column(Text, default="", nullable=False)
    sent_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Sanitized plain text extracted from email body
    snippet: Mapped[str] = mapped_column(Text, default="", nullable=False)
    body_plain: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # AI processing state
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_relevant: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    generation: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    mailbox: Mapped["MailboxAccount"] = relationship("MailboxAccount", back_populates="messages")
