"""
AES-256 Encryption for sensitive data.

Mengenkripsi data sensitif (API keys, secrets) sebelum disimpan ke database.
Dekripsi hanya dilakukan saat data dibutuhkan.

Usage:
    from app.core.encryption import encrypt, decrypt
    encrypted = encrypt("my-secret-api-key")   # → "gAAAAABh..."
    original = decrypt(encrypted)               # → "my-secret-api-key"
"""

from cryptography.fernet import Fernet
from app.core.config import settings
import base64
import hashlib

def _get_key() -> bytes:
    """Get encryption key from ENCRYPTION_KEY."""
    if not settings.ENCRYPTION_KEY:
        raise ValueError("ENCRYPTION_KEY is missing from environment. Application cannot start securely.")
    return settings.ENCRYPTION_KEY.encode()

def encrypt(plaintext: str) -> str:
    """Enkripsi string → encrypted string."""
    if not plaintext:
        return plaintext
    f = Fernet(_get_key())
    return f.encrypt(plaintext.encode()).decode()

def decrypt(ciphertext: str) -> str:
    """Dekripsi encrypted string → original string."""
    if not ciphertext:
        return ciphertext
    f = Fernet(_get_key())
    return f.decrypt(ciphertext.encode()).decode()
