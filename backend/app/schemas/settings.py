from pydantic import BaseModel


class SettingsResponse(BaseModel):
    timezone: str
    is_demo_mode: bool
    is_setup_completed: bool
    mailbox_email: str | None = None
    sync_status: str = "idle"
    has_google_credentials: bool = False
    ai_provider: str = "pydantic-ai"


class UpdateSettingsRequest(BaseModel):
    timezone: str | None = None
    is_demo_mode: bool | None = None


class LifecycleActionResponse(BaseModel):
    message: str
    status: str
