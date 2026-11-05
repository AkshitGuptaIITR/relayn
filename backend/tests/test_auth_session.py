import pytest
from app.auth.session import SessionEncryptionError, SessionManager


def test_session_encrypt_and_decrypt():
    # 32 bytes hex key
    secret = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    manager = SessionManager(secret_hex=secret)

    payload = {"authenticated": True, "csrf_token": "test_token_123"}
    token = manager.create_session_token(payload, max_age_seconds=60)

    decoded = manager.decode_session_token(token)
    assert decoded["authenticated"] is True
    assert decoded["csrf_token"] == "test_token_123"
    assert "exp" in decoded
    assert "iat" in decoded


def test_session_forgery_fails():
    secret = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    manager = SessionManager(secret_hex=secret)

    token = manager.create_session_token({"authenticated": True})

    # Tamper with the token
    tampered_token = token[:-5] + "AAAAA"
    with pytest.raises(SessionEncryptionError):
        manager.decode_session_token(tampered_token)


def test_session_expired():
    secret = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    manager = SessionManager(secret_hex=secret)

    # Max age negative -> already expired
    token = manager.create_session_token({"authenticated": True}, max_age_seconds=-10)
    with pytest.raises(SessionEncryptionError, match="Session token has expired"):
        manager.decode_session_token(token)
