import datetime
import uuid
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class InstallationState(Base, TimestampMixin):
    """Singleton row tracking owner installation state, demo mode, and preferences."""

    __tablename__ = "installation_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False, default=1)
    is_setup_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_demo_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    owner_email: Mapped[str | None] = mapped_column(String(255), nullable=True)


class AuthAttempt(Base):
    """Rate-limiting and audit log for local login attempts."""

    __tablename__ = "auth_attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    attempted_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    is_successful: Mapped[bool] = mapped_column(Boolean, nullable=False)


class OAuthSessionState(Base, TimestampMixin):
    """Google OAuth PKCE and one-time CSRF state verification records."""

    __tablename__ = "oauth_session_states"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    state_token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    code_verifier: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
