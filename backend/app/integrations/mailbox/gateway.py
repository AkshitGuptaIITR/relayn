import datetime
from pydantic import BaseModel, Field


class IngestedMessage(BaseModel):
    """Standardized normalized email message produced by any mailbox gateway."""

    gmail_message_id: str = Field(..., description="Unique message ID")
    gmail_thread_id: str = Field(..., description="Gmail or conversation thread ID")
    history_id: str | None = Field(default=None, description="Mailbox sync cursor / history ID")
    sender: str
    recipients: list[str] = Field(default_factory=list)
    subject: str = ""
    sent_at: datetime.datetime
    snippet: str = ""
    body_plain: str = ""


class SyncResult(BaseModel):
    """Result of a sync iteration."""

    messages: list[IngestedMessage]
    new_history_id: str | None = None
    has_more: bool = False
