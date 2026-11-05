import base64
import json
import os
import time
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.core.config import settings


class SessionEncryptionError(Exception):
    """Raised when session decryption or verification fails."""
    pass


class SessionManager:
    """Handles AES-256-GCM stateless encrypted session cookies."""

    def __init__(self, secret_hex: str | None = None):
        hex_key = secret_hex or settings.RELAYN_SESSION_SECRET
        if not hex_key:
            raise ValueError("RELAYN_SESSION_SECRET must be configured")
        self.key = bytes.fromhex(hex_key)
        self.aesgcm = AESGCM(self.key)

    def create_session_token(self, data: dict, max_age_seconds: int = 86400 * 7) -> str:
        """
        Encrypts session payload into a compact URL-safe base64 string.
        Includes an expiration timestamp and nonce.
        """
        payload = {
            **data,
            "exp": int(time.time()) + max_age_seconds,
            "iat": int(time.time()),
        }
        json_bytes = json.dumps(payload).encode("utf-8")
        
        # 12-byte nonce standard for AES-GCM
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, json_bytes, None)
        
        # Combine nonce (12 bytes) + ciphertext (includes 16-byte auth tag)
        packed = nonce + ciphertext
        return base64.urlsafe_b64encode(packed).decode("utf-8")

    def decode_session_token(self, token: str) -> dict:
        """
        Decrypts and verifies the session token.
        Raises SessionEncryptionError if forged, altered, or expired.
        """
        try:
            packed = base64.urlsafe_b64decode(token.encode("utf-8"))
            if len(packed) < 12 + 16:  # nonce (12) + auth tag (16)
                raise SessionEncryptionError("Invalid token format")
            
            nonce = packed[:12]
            ciphertext = packed[12:]
            
            plaintext = self.aesgcm.decrypt(nonce, ciphertext, None)
            payload = json.loads(plaintext.decode("utf-8"))
            
            # Check expiration
            exp = payload.get("exp", 0)
            if time.time() > exp:
                raise SessionEncryptionError("Session token has expired")
                
            return payload
        except SessionEncryptionError:
            raise
        except Exception as e:
            raise SessionEncryptionError(f"Failed to decrypt session: {e}") from e
