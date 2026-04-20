# Epic 14: Security Hardening

---

## T-14.1: AES-256 Encryption untuk API Keys Exchange

**Labels:** `epic-14`, `security`, `encryption`, `priority-critical`
**Milestone:** Fase 6 — Hardening

### Deskripsi
API keys exchange (Bybit/Binance) yang disimpan di database harus dienkripsi menggunakan AES-256. Jika database diretas, penyerang tidak bisa langsung mendapatkan API keys.

### Mengapa?
`.env` hanya melindungi di repository. Tapi jika bot menyimpan API keys di database (misalnya untuk multi-exchange config), keys tersebut harus dienkripsi.

### Langkah-Langkah

#### 1. Buat `backend/app/core/encryption.py`

```python
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
    f = Fernet(_get_key())
    return f.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Dekripsi encrypted string → original string."""
    f = Fernet(_get_key())
    return f.decrypt(ciphertext.encode()).decode()
```

#### 2. Gunakan di model database
```python
class ExchangeConfig(Base):
    __tablename__ = "exchange_configs"
    
    id = Column(Integer, primary_key=True)
    exchange_name = Column(String, nullable=False)
    api_key_encrypted = Column(String, nullable=False)  # Encrypted
    api_secret_encrypted = Column(String, nullable=False)  # Encrypted
    
    def set_api_key(self, key: str):
        self.api_key_encrypted = encrypt(key)
    
    def get_api_key(self) -> str:
        return decrypt(self.api_key_encrypted)
```

### Definition of Done
- [ ] `encrypt()` dan `decrypt()` berfungsi
- [ ] API keys dienkripsi sebelum disimpan di DB
- [ ] Dekripsi hanya saat dibutuhkan
- [ ] Jika DB leaked, API keys TIDAK readable
- [ ] Unit test enkripsi/dekripsi

### File yang Dibuat
- `[NEW]` `backend/app/core/encryption.py`

---

## T-14.2: JWT Authentication (Access + Refresh Token)

**Labels:** `epic-14`, `security`, `auth`, `priority-critical`
**Milestone:** Fase 6 — Hardening

### Deskripsi
Implementasi JWT (JSON Web Token) authentication yang aman.

### Flow
1. User login → server generate **access token** (short-lived, 1 jam) + **refresh token** (long-lived, 7 hari)
2. Client kirim access token di header setiap request: `Authorization: Bearer <token>`
3. Server validate token di setiap endpoint
4. Saat access token expired → client kirim refresh token → server kasih access token baru
5. Refresh token disimpan di database (agar bisa di-revoke)

### Langkah-Langkah
1. Buat `backend/app/core/security.py`
2. `create_access_token(user_id, expires_delta=timedelta(hours=1))`
3. `create_refresh_token(user_id, expires_delta=timedelta(days=7))`
4. `verify_token(token) → user_id` (raise error jika invalid/expired)
5. Dependency injection: `get_current_user = Depends(verify_token)`
6. Refresh token rotation: setiap kali refresh, invalidate token lama dan buat baru

### Definition of Done
- [ ] Access token (1 jam) + refresh token (7 hari)
- [ ] Token verification di setiap protected endpoint
- [ ] Refresh token rotation
- [ ] Token bisa di-revoke (logout)
- [ ] Expired token → 401 response

### File yang Dibuat
- `[NEW]` `backend/app/core/security.py`

---

## T-14.3: 2FA (TOTP) Implementation

**Labels:** `epic-14`, `security`, `auth`, `priority-critical`
**Milestone:** Fase 6 — Hardening
**Depends On:** T-14.2

### Deskripsi
Implementasi Two-Factor Authentication menggunakan TOTP (Time-based One-Time Password). User harus memasukkan kode 6 digit dari Google Authenticator setelah password.

### Langkah-Langkah
1. Install: `pip install pyotp qrcode`
2. Saat user pertama kali setup: generate TOTP secret → tampilkan QR code → user scan dengan Google Authenticator
3. Saat login: setelah password benar, minta kode 6 digit → verifikasi dengan `pyotp.TOTP(secret).verify(code)`
4. TOTP secret disimpan terenkripsi di database (pakai T-14.1)

### Implementasi
```python
import pyotp

def setup_2fa(user_id: str) -> dict:
    """Generate TOTP secret dan QR code URL."""
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=user_id, issuer_name="APEX Trading Bot")
    return {"secret": secret, "qr_uri": uri}

def verify_2fa(secret: str, code: str) -> bool:
    """Verifikasi kode TOTP."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)  # Allow 1 period tolerance
```

### Definition of Done
- [ ] QR code bisa di-scan oleh Google Authenticator
- [ ] Kode 6 digit terverifikasi dengan benar
- [ ] TOTP secret terenkripsi di database
- [ ] Login flow: password → 2FA → JWT token

---

## T-14.4: Rate Limiting pada Login Endpoint

**Labels:** `epic-14`, `security`, `priority-high`
**Milestone:** Fase 6 — Hardening

### Deskripsi
Membatasi jumlah percobaan login untuk mencegah brute force attack.

### Rules
- Max 5 login attempts per IP per 15 menit
- Max 10 login attempts per account per 30 menit
- Setelah limit tercapai: block selama 15 menit
- Alert jika ada >20 attempts dari 1 IP (possible attack)

### Langkah-Langkah
1. Gunakan Redis untuk tracking attempt count
2. Key format: `login_attempt:ip:{ip}` dan `login_attempt:user:{username}`
3. Increment on failed login, reset on successful login
4. Return 429 Too Many Requests jika limit tercapai

### Definition of Done
- [ ] Rate limiting berfungsi per IP dan per account
- [ ] 429 response saat limit tercapai
- [ ] Auto-unblock setelah cooling period
- [ ] Alert untuk suspicious activity

---

## T-14.5: Audit Log

**Labels:** `epic-14`, `security`, `observability`, `priority-high`
**Milestone:** Fase 6 — Hardening

### Deskripsi
Mencatat setiap aksi penting yang dilakukan di dashboard untuk audit trail.

### Events yang Dicatat
- Login (sukses/gagal)
- Logout
- Bot start/stop
- Mode switch (paper/live)
- Settings change
- Manual position close
- API key update

### Format Log
```json
{
    "timestamp": "2026-04-20T10:30:00Z",
    "user": "admin",
    "action": "bot_mode_switch",
    "details": {"from": "paper", "to": "live"},
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0..."
}
```

### Definition of Done
- [ ] Semua events tercatat di database
- [ ] Timestamp + user + action + details
- [ ] Bisa di-query via API (untuk admin dashboard)
- [ ] Tidak bisa dihapus/dimodifikasi (append-only)

### File yang Dibuat
- `[NEW]` `backend/app/services/audit_log.py`
- `[NEW]` `backend/app/models/audit_log.py`

---

## T-14.6: HTTPS Enforcement

**Labels:** `epic-14`, `security`, `infrastructure`, `priority-critical`
**Milestone:** Fase 6 — Hardening

### Deskripsi
Memastikan semua komunikasi dashboard di-enkripsi via HTTPS (TLS).

### Langkah-Langkah
1. Setup Nginx/Caddy sebagai reverse proxy
2. SSL certificate via Let's Encrypt (Caddy otomatis) atau self-signed (development)
3. HTTP → HTTPS redirect
4. HSTS header: `Strict-Transport-Security: max-age=31536000`

### Definition of Done
- [ ] Dashboard hanya bisa diakses via HTTPS
- [ ] HTTP redirect ke HTTPS
- [ ] SSL certificate valid

---

## T-14.7: `.gitignore` Review & Hardening

**Labels:** `epic-14`, `security`, `priority-critical`
**Milestone:** Fase 6 — Hardening

### Deskripsi
Review final `.gitignore` memastikan ZERO chance kebocoran data sensitif. Termasuk scanning git history untuk file sensitif yang mungkin sudah pernah di-commit.

### Langkah-Langkah
1. Review `.gitignore` rules (dari T-1.1)
2. Scan git history: `git log --all --full-history -- "*.env" "*.key" "*.pem"`
3. Jika ditemukan: gunakan `git filter-branch` atau `BFG Repo-Cleaner` untuk menghapus
4. Tambah pre-commit hook yang menolak file sensitif

### Pre-commit Hook
```bash
#!/bin/sh
# .git/hooks/pre-commit

# Check for sensitive file patterns
SENSITIVE_PATTERNS=".env$|\.key$|\.pem$|\.secret|api_key|secret_key"
FILES=$(git diff --cached --name-only | grep -iE "$SENSITIVE_PATTERNS")

if [ -n "$FILES" ]; then
    echo "❌ BLOCKED: Attempting to commit sensitive files:"
    echo "$FILES"
    echo "Remove these files from staging with: git reset HEAD <file>"
    exit 1
fi
```

### Definition of Done
- [ ] Git history bersih dari file sensitif
- [ ] Pre-commit hook aktif
- [ ] `.gitignore` komprehensif dan reviewed

---

## T-14.8: Security Scanning di CI/CD

**Labels:** `epic-14`, `security`, `devops`, `priority-medium`
**Milestone:** Fase 6 — Hardening

### Deskripsi
Menambahkan dependency vulnerability scanning di CI/CD pipeline.

### Langkah-Langkah
1. Python: `pip install safety` → `safety check` (scan vulnerable packages)
2. Node.js: `npm audit` (built-in)
3. Secret scanning: grep untuk pattern API key di codebase
4. Tambahkan ke GitHub Actions (T-1.5)

### Definition of Done
- [ ] Python dependency scan di CI
- [ ] Node.js dependency scan di CI
- [ ] Secret pattern scan di CI
- [ ] Build gagal jika ada vulnerability critical

---

## T-14.9: CORS Configuration

**Labels:** `epic-14`, `security`, `api`, `priority-high`
**Milestone:** Fase 6 — Hardening

### Deskripsi
Konfigurasi CORS (Cross-Origin Resource Sharing) agar hanya domain dashboard yang bisa mengakses API.

### Langkah-Langkah
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.NEXTAUTH_URL,  # Dashboard URL
        "http://localhost:3000",  # Development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### Definition of Done
- [ ] Hanya allowed origins yang bisa akses API
- [ ] Development URL diperbolehkan
- [ ] Production URL dikonfigurasi
- [ ] Wildcard `*` TIDAK digunakan di production
