import datetime
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.auth import AuthAttempt

ph = PasswordHasher()

# Rate limit rules: max 5 failed attempts per 15 minutes per IP
RATE_LIMIT_WINDOW_MINUTES = 15
MAX_FAILED_ATTEMPTS = 5


def verify_owner_password(password: str) -> bool:
    """Verifies plain password against RELAYN_PASSWORD_HASH using Argon2id."""
    if not settings.RELAYN_PASSWORD_HASH:
        return False
    try:
        return ph.verify(settings.RELAYN_PASSWORD_HASH, password)
    except (VerifyMismatchError, Exception):
        return False


async def is_rate_limited(ip_address: str, db: AsyncSession) -> bool:
    """Checks if an IP has exceeded the allowed failed login attempts."""
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        minutes=RATE_LIMIT_WINDOW_MINUTES
    )
    stmt = (
        select(func.count(AuthAttempt.id))
        .where(AuthAttempt.ip_address == ip_address)
        .where(AuthAttempt.is_successful == False)
        .where(AuthAttempt.attempted_at >= since)
    )
    result = await db.execute(stmt)
    failed_count = result.scalar() or 0
    return failed_count >= MAX_FAILED_ATTEMPTS


async def record_auth_attempt(ip_address: str, is_successful: bool, db: AsyncSession) -> None:
    """Records an auth attempt into the database audit log."""
    attempt = AuthAttempt(
        ip_address=ip_address,
        is_successful=is_successful,
    )
    db.add(attempt)
    await db.commit()
