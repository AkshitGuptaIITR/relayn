import base64
import datetime
import hashlib
import json
import os
import secrets
import urllib.parse
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.auth import OAuthSessionState
from app.models.mailbox import MailboxAccount

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class GoogleOAuthService:
    """
    Handles Google OAuth 2.0 Web Client Authorization with PKCE & CSRF protection:
    - Generates cryptographically random state tokens & PKCE code verifiers
    - Builds authorization redirect URLs strictly requesting gmail.readonly
    - Exchanges authorization code for refresh tokens
    - Encrypts stored credentials using AES-256-GCM
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        if not settings.RELAYN_SESSION_SECRET:
            raise ValueError("RELAYN_SESSION_SECRET is required to encrypt Google OAuth tokens")
        self.aesgcm = AESGCM(bytes.fromhex(settings.RELAYN_SESSION_SECRET))

    async def create_authorization_url(self, redirect_uri: str) -> str:
        """
        Creates PKCE code_verifier, code_challenge, and state token.
        Persists state in oauth_session_states for single-use verification.
        """
        if not settings.GOOGLE_CLIENT_ID:
            raise ValueError("GOOGLE_CLIENT_ID must be configured in environment or .env")

        # 1. Generate high-entropy state and PKCE verifier
        state_token = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)

        # 2. Compute S256 code challenge
        challenge_bytes = hashlib.sha256(code_verifier.encode("ascii")).digest()
        code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode("ascii").rstrip("=")

        # 3. Store in DB with 15-minute expiration
        now = datetime.datetime.now(datetime.timezone.utc)
        expires_at = now + datetime.timedelta(minutes=15)

        oauth_state = OAuthSessionState(
            state_token=state_token,
            code_verifier=code_verifier,
            expires_at=expires_at,
            is_used=False,
        )
        self.db.add(oauth_state)
        await self.db.commit()

        # 4. Construct Google authorization URL
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": GMAIL_READONLY_SCOPE,
            "access_type": "offline",  # Requests refresh_token
            "prompt": "consent",        # Forces consent screen to ensure refresh_token is returned
            "state": state_token,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def verify_and_consume_state(self, state_token: str) -> str:
        """
        Verifies state token is valid, unused, and unexpired.
        Marks it as used immediately (single-use defense against replay attacks)
        and returns the associated PKCE code_verifier.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        stmt = select(OAuthSessionState).where(
            OAuthSessionState.state_token == state_token,
            OAuthSessionState.is_used == False,
            OAuthSessionState.expires_at > now,
        )
        res = await self.db.execute(stmt)
        record = res.scalar_one_or_none()

        if not record:
            raise ValueError("Invalid, expired, or already used OAuth state parameter")

        record.is_used = True
        await self.db.commit()
        return record.code_verifier

    def encrypt_credentials(self, credentials_data: dict) -> str:
        """Encrypts credentials dictionary to a compact URL-safe base64 string."""
        raw_json = json.dumps(credentials_data).encode("utf-8")
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, raw_json, None)
        return base64.urlsafe_b64encode(nonce + ciphertext).decode("utf-8")

    def decrypt_credentials(self, encrypted_token: str) -> dict:
        """Decrypts encrypted credentials string back into credentials dictionary."""
        packed = base64.urlsafe_b64decode(encrypted_token.encode("utf-8"))
        nonce = packed[:12]
        ciphertext = packed[12:]
        plaintext = self.aesgcm.decrypt(nonce, ciphertext, None)
        return json.loads(plaintext.decode("utf-8"))
