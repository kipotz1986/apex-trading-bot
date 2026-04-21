"""
AES-256 Encryption for sensitive data.
Using cryptography.fernet for symmetric encryption of API keys.
"""

import base64
import hashlib
from cryptography.fernet import Fernet
from app.core.config import settings

def _get_key() -> bytes:
    """Derive encryption key from JWT_SECRET to ensure uniqueness per installation."""
    # Use SHA-256 to create a 32-byte key from the JWT_SECRET
    key = hashlib.sha256(settings.JWT_SECRET.encode()).digest()
    return base64.urlsafe_b64encode(key)

def encrypt(plaintext: str) -> str:
    """Encrypts a string into a Fernet token."""
    if not plaintext:
        return ""
    f = Fernet(_get_key())
    return f.encrypt(plaintext.encode()).decode()

def decrypt(ciphertext: str) -> str:
    """Decrypts a Fernet token back into the original string."""
    if not ciphertext:
        return ""
    try:
        f = Fernet(_get_key())
        return f.decrypt(ciphertext.encode()).decode()
    except Exception:
        # If decryption fails (e.g. wrong key), return empty string or handle error
        return ""
