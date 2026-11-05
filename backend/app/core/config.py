from pathlib import Path
from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Locate root .env (parent of backend/ directory)
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BACKEND_DIR.parent
ENV_PATH = ROOT_DIR / ".env"


class Settings(BaseSettings):
    """Validated environment settings for Relayn."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH) if ENV_PATH.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application & Network
    RELAYN_ENV: Literal["development", "production", "test"] = "development"
    RELAYN_PORT: int = 8000
    RELAYN_HOST: str = "127.0.0.1"
    RELAYN_APP_URL: str = "http://localhost:3000"

    # Security
    RELAYN_PASSWORD_HASH: str = Field(
        default="",
        description="Argon2id hash of the local owner password",
    )
    RELAYN_SESSION_SECRET: str = Field(
        default="",
        description="32-byte (64 hex characters) secret for AES-256-GCM session cookie encryption",
    )

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/relayn",
        description="Async PostgreSQL connection string",
    )

    # Owner Preferences
    RELAYN_TIMEZONE: str = "UTC"

    # AI Provider
    AI_PROVIDER: Literal["fixtures", "gemini"] = "fixtures"
    GEMINI_API_KEY: str | None = None

    # Google OAuth (Phase 5)
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None

    @field_validator("RELAYN_SESSION_SECRET")
    @classmethod
    def validate_session_secret(cls, v: str, info) -> str:
        # In test mode, allow empty default or test value
        if not v:
            return v
        if len(v) != 64:
            try:
                # Also check if it's 32 raw bytes length or hex string
                raw_bytes = bytes.fromhex(v)
                if len(raw_bytes) != 32:
                    raise ValueError("RELAYN_SESSION_SECRET must decode to exactly 32 bytes")
            except ValueError:
                raise ValueError("RELAYN_SESSION_SECRET must be a 64-character hex string (32 bytes)")
        return v

    @field_validator("RELAYN_PASSWORD_HASH")
    @classmethod
    def validate_password_hash(cls, v: str, info) -> str:
        if not v:
            return v
        if not v.startswith("$argon2"):
            raise ValueError("RELAYN_PASSWORD_HASH must be an Argon2id formatted hash (starts with $argon2)")
        return v


settings = Settings()
