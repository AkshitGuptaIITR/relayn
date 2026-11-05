import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_authenticated_owner
from app.auth.google_oauth import GOOGLE_TOKEN_URL, GoogleOAuthService
from app.core.config import settings
from app.db.session import get_db_session
from app.models.mailbox import MailboxAccount

router = APIRouter(prefix="/api/auth/google", tags=["google-oauth"])


def get_redirect_uri(request: Request) -> str:
    # Google OAuth callback URL (e.g. http://localhost:8000/api/auth/google/callback or owner host)
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/auth/google/callback"


@router.get("/connect")
async def connect_google(
    request: Request,
    session: dict = Depends(require_authenticated_owner),
    db: AsyncSession = Depends(get_db_session),
):
    """Generates state + PKCE and redirects owner to Google OAuth consent screen."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google Client ID and Secret must be configured in settings/.env to connect real Gmail.",
        )

    oauth_service = GoogleOAuthService(db)
    redirect_uri = get_redirect_uri(request)
    auth_url = await oauth_service.create_authorization_url(redirect_uri=redirect_uri)
    return {"authorization_url": auth_url}


@router.get("/callback")
async def google_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    error: str | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handles Google OAuth redirect:
    1. Verifies and consumes single-use state + retrieves PKCE code_verifier.
    2. Exchanges authorization code for tokens.
    3. Fetches user profile from Gmail API to obtain mailbox email address.
    4. Encrypts and persists tokens in MailboxAccount.
    5. Redirects back to frontend Settings/Dashboard.
    """
    if error:
        return RedirectResponse(url=f"{settings.RELAYN_APP_URL}/settings?error={error}")

    oauth_service = GoogleOAuthService(db)
    try:
        code_verifier = await oauth_service.verify_and_consume_state(state)
    except ValueError as e:
        return RedirectResponse(url=f"{settings.RELAYN_APP_URL}/settings?error=invalid_oauth_state")

    redirect_uri = get_redirect_uri(request)

    # 1. Exchange code with PKCE verifier
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "code_verifier": code_verifier,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )

    if token_resp.status_code != 200:
        return RedirectResponse(url=f"{settings.RELAYN_APP_URL}/settings?error=token_exchange_failed")

    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")

    # 2. Get connected mailbox address via Gmail Profile API
    async with httpx.AsyncClient() as client:
        profile_resp = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/profile",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if profile_resp.status_code != 200:
        return RedirectResponse(url=f"{settings.RELAYN_APP_URL}/settings?error=profile_fetch_failed")

    user_email = profile_resp.json().get("emailAddress", "connected@gmail.com")

    # 3. Encrypt and persist credentials into MailboxAccount
    encrypted_creds = oauth_service.encrypt_credentials({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_uri": GOOGLE_TOKEN_URL,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
    })

    stmt = select(MailboxAccount).limit(1)
    res = await db.execute(stmt)
    mailbox = res.scalar_one_or_none()

    if not mailbox:
        mailbox = MailboxAccount(
            email_address=user_email,
            encrypted_credentials=encrypted_creds,
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
            sync_status="idle",
        )
        db.add(mailbox)
    else:
        mailbox.email_address = user_email
        mailbox.encrypted_credentials = encrypted_creds
        mailbox.sync_status = "idle"
        mailbox.sync_error = None

    await db.commit()

    return RedirectResponse(url=f"{settings.RELAYN_APP_URL}/settings?connected=true")
