"""Fernet-based token encryption for calendar credentials."""
from __future__ import annotations

from app.config import get_settings


def _get_fernet():
    from cryptography.fernet import Fernet
    settings = get_settings()
    key = settings.fernet_key
    if not key:
        # Generate a temporary key (tokens won't survive restart without a real key)
        key = Fernet.generate_key().decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_token(plaintext: str) -> str:
    if not plaintext:
        return plaintext
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str | None) -> str:
    if not ciphertext:
        return ""
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except Exception:
        # Token may be stored unencrypted (dev/migration fallback)
        return ciphertext
