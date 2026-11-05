import secrets
from fastapi import Cookie, Depends, HTTPException, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.session import SessionEncryptionError, SessionManager
from app.db.session import get_db_session

COOKIE_NAME = "relayn_session"
CSRF_HEADER_NAME = "x-csrf-token"


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, taking loopback or proxy into account."""
    if request.client:
        return request.client.host
    return "127.0.0.1"


def get_session_manager() -> SessionManager:
    return SessionManager()


async def get_current_session(
    request: Request,
    relayn_session: str | None = Cookie(default=None),
    session_manager: SessionManager = Depends(get_session_manager),
) -> dict:
    """Dependency that extracts and validates the encrypted session cookie."""
    if not relayn_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    try:
        payload = session_manager.decode_session_token(relayn_session)
        return payload
    except SessionEncryptionError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )


async def require_authenticated_owner(
    request: Request,
    session: dict = Depends(get_current_session),
    x_csrf_token: str | None = Header(default=None, alias=CSRF_HEADER_NAME),
) -> dict:
    """
    Guards endpoints:
    1. Verifies authenticated owner in session.
    2. Validates CSRF token for state-mutating requests (POST, PUT, DELETE, PATCH).
    """
    if not session.get("authenticated"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    # CSRF Check on mutating methods
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        expected_csrf = session.get("csrf_token")
        if not expected_csrf or not x_csrf_token or not secrets.compare_digest(expected_csrf, x_csrf_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or missing CSRF token",
            )

    return session
