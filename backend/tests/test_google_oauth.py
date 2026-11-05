import pytest
from app.auth.google_oauth import GoogleOAuthService
from app.db.session import async_session_factory


@pytest.mark.asyncio
async def test_google_oauth_pkce_and_state_generation():
    async with async_session_factory() as session:
        oauth_service = GoogleOAuthService(session)

        # Test encryption & decryption of token payload
        payload = {"access_token": "secret_abc", "refresh_token": "secret_xyz"}
        encrypted = oauth_service.encrypt_credentials(payload)
        decrypted = oauth_service.decrypt_credentials(encrypted)
        assert decrypted["access_token"] == "secret_abc"
        assert decrypted["refresh_token"] == "secret_xyz"

        # Test single-use state verification and replay attack rejection
        from app.models.auth import OAuthSessionState
        import datetime

        # Insert test state
        now = datetime.datetime.now(datetime.timezone.utc)
        record = OAuthSessionState(
            state_token="valid_state_123",
            code_verifier="test_verifier_456",
            expires_at=now + datetime.timedelta(minutes=10),
            is_used=False,
        )
        session.add(record)
        await session.commit()

        # 1. First consumption succeeds
        verifier = await oauth_service.verify_and_consume_state("valid_state_123")
        assert verifier == "test_verifier_456"

        # 2. Replay attack: second consumption with same state MUST fail
        with pytest.raises(ValueError, match="Invalid, expired, or already used"):
            await oauth_service.verify_and_consume_state("valid_state_123")
