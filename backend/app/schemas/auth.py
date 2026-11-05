from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    password: str = Field(..., min_length=1)


class AuthStatusResponse(BaseModel):
    authenticated: bool
    csrf_token: str | None = None
    timezone: str = "UTC"
    is_setup_completed: bool = False
    is_demo_mode: bool = False
