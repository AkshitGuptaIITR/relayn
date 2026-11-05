import secrets
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    COOKIE_NAME,
    get_client_ip,
    get_session_manager,
    require_authenticated_owner,
)
from app.auth.security import is_rate_limited, record_auth_attempt, verify_owner_password
from app.auth.session import SessionManager
from app.core.config import settings
from app.db.session import get_db_session
from app.models.auth import InstallationState
from app.schemas.auth import AuthStatusResponse, LoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


async def get_or_create_installation_state(db: AsyncSession) -> InstallationState:
    stmt = select(InstallationState).where(InstallationState.id == 1)
    result = await db.execute(stmt)
    state = result.scalar_one_or_none()
    if not state:
        state = InstallationState(
            id=1,
            timezone=settings.RELAYN_TIMEZONE,
            is_setup_completed=False,
            is_demo_mode=False,
        )
        db.add(state)
        await db.commit()
        await db.refresh(state)
    return state


@router.post("/login", response_model=AuthStatusResponse)
async def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
    session_manager: SessionManager = Depends(get_session_manager),
):
    client_ip = get_client_ip(request)

    # 1. Check rate limits
    if await is_rate_limited(client_ip, db):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please wait 15 minutes before trying again.",
        )

    # 2. Verify password
    is_valid = verify_owner_password(payload.password)
    await record_auth_attempt(client_ip, is_successful=is_valid, db=db)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid master password",
        )

    # 3. Issue CSRF token & encrypted session cookie
    csrf_token = secrets.token_hex(32)
    session_data = {
        "authenticated": True,
        "csrf_token": csrf_token,
        "ip": client_ip,
    }
    session_cookie = session_manager.create_session_token(session_data)

    # Set secure, HTTP-only, SameSite=Lax cookie
    is_prod = settings.RELAYN_ENV == "production"
    response.set_cookie(
        key=COOKIE_NAME,
        value=session_cookie,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=86400 * 7,  # 7 days
    )

    state = await get_or_create_installation_state(db)
    return AuthStatusResponse(
        authenticated=True,
        csrf_token=csrf_token,
        timezone=state.timezone,
        is_setup_completed=state.is_setup_completed,
        is_demo_mode=state.is_demo_mode,
    )


@router.get("/me", response_model=AuthStatusResponse)
async def me(
    request: Request,
    relayn_session: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db_session),
    session_manager: SessionManager = Depends(get_session_manager),
):
    state = await get_or_create_installation_state(db)
    if not relayn_session:
        return AuthStatusResponse(
            authenticated=False,
            timezone=state.timezone,
            is_setup_completed=state.is_setup_completed,
            is_demo_mode=state.is_demo_mode,
        )

    try:
        data = session_manager.decode_session_token(relayn_session)
        return AuthStatusResponse(
            authenticated=True,
            csrf_token=data.get("csrf_token"),
            timezone=state.timezone,
            is_setup_completed=state.is_setup_completed,
            is_demo_mode=state.is_demo_mode,
        )
    except Exception:
        return AuthStatusResponse(
            authenticated=False,
            timezone=state.timezone,
            is_setup_completed=state.is_setup_completed,
            is_demo_mode=state.is_demo_mode,
        )


@router.post("/logout")
async def logout(
    response: Response,
    session: dict = Depends(require_authenticated_owner),
):
    response.delete_cookie(key=COOKIE_NAME)
    return {"message": "Logged out successfully"}
