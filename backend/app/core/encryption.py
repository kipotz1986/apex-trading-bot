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
    """Derive encryption key dari JWT_SECRET."""
    # Gunakan JWT_SECRET sebagai basis key
    key = hashlib.sha256(settings.JWT_SECRET.encode()).digest()
    return base64.urlsafe_b64encode(key)

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
