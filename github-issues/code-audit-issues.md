# Code Audit Issues — APEX Trading Bot

> **Ditemukan 15 issue** dari code review menyeluruh.
> Dikategorikan: 🔴 Critical Bug, 🟡 Security, 🔵 Refactor

---

## Issue #1: 🔴 [BUG] `auth.py` — Missing `Request` import menyebabkan NameError saat login

**Labels:** `bug`, `priority-critical`, `epic-14`

### Deskripsi Bug
Fungsi `login()` di `backend/app/api/auth.py` line 32 menggunakan type hint `request: Request` sebagai parameter, tetapi class `Request` **tidak pernah di-import** dari `fastapi`.

### Dampak
Server akan **crash** dengan `NameError: name 'Request' is not defined` setiap kali endpoint `POST /api/auth/login` dipanggil. Ini berarti **tidak ada user yang bisa login** ke dashboard.

### Lokasi Kode
- **File**: `backend/app/api/auth.py`, line 5 dan line 32
- **Line 5** (import saat ini):
```python
from fastapi import APIRouter, Depends, HTTPException, status
```
- **Line 32** (penggunaan yang error):
```python
async def login(request: Request, form_data: ...):
```

### Cara Repro
1. Jalankan backend: `python3 -m uvicorn app.main:app`
2. Kirim POST request ke `/api/auth/login` dengan form data username/password
3. Server akan crash dengan traceback `NameError`

### Solusi (Step-by-step)

#### Step 1: Tambahkan `Request` ke import
Buka file `backend/app/api/auth.py`, ubah line 5 dari:
```python
from fastapi import APIRouter, Depends, HTTPException, status
```
menjadi:
```python
from fastapi import APIRouter, Depends, HTTPException, status, Request
```

#### Step 2: Verifikasi
```bash
cd backend
python3 -c "from app.api.auth import router; print('OK')"
```

### Definition of Done
- [ ] `Request` di-import dari `fastapi`
- [ ] Endpoint `/api/auth/login` bisa dipanggil tanpa crash
- [ ] Test manual memverifikasi login flow berjalan

---

## Issue #2: 🔴 [BUG] `auth.py` — Broken indentation pada password verification logic

**Labels:** `bug`, `priority-critical`, `epic-14`

### Deskripsi Bug
Logika verifikasi password di `backend/app/api/auth.py` line 43-56 memiliki **indentasi yang rusak** akibat refactoring yang tidak sempurna. Guard condition `if settings.ADMIN_PASSWORD_HASH:` hilang, sehingga:
- Blok `else` (line 50) menggantung dan tidak terhubung dengan `if` yang benar
- Password check akan **selalu gagal** atau menyebabkan **SyntaxError**

### Lokasi Kode
**File**: `backend/app/api/auth.py` line 43-56

**Kode saat ini (RUSAK):**
```python
    # Check password hash (if set, otherwise allow 'admin' for initial setup)
        if not security.verify_password(form_data.password, settings.ADMIN_PASSWORD_HASH):
            log_audit(db, "login_failed", ...)
            raise HTTPException(...)
    else:
        # Emergency fallback for initial setup
        if form_data.password != "admin":
             raise HTTPException(...)
```

Perhatikan indentasi tidak konsisten — `if not security.verify_password` lebih dalam dari yang seharusnya, dan `else` tidak sejajar dengan `if` manapun.

### Solusi

Ganti blok line 43-56 dengan kode berikut:
```python
    # Check password hash (if set, otherwise allow 'admin' for initial setup)
    if settings.ADMIN_PASSWORD_HASH:
        if not security.verify_password(form_data.password, settings.ADMIN_PASSWORD_HASH):
            log_audit(db, "login_failed", form_data.username, {"reason": "wrong_password"}, ip_address=request.client.host)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )
    else:
        # Emergency fallback for initial setup only
        if form_data.password != "admin":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )
```

### Definition of Done
- [ ] Indentasi diperbaiki sehingga `if/else` sejajar
- [ ] Login berhasil saat `ADMIN_PASSWORD_HASH` diisi dan password benar
- [ ] Login berhasil saat `ADMIN_PASSWORD_HASH` kosong dan password "admin"
- [ ] Login gagal saat password salah

---

## Issue #3: 🔴 [BUG] `agents.py` — AttributeError karena salah nama kolom `metadata_json` vs `meta_data`

**Labels:** `bug`, `priority-critical`, `epic-13`

### Deskripsi Bug
Di `backend/app/api/agents.py` line 40, kode mengakses `o.metadata_json` tetapi model `Order` (di `backend/app/models/order.py` line 54) mendefinisikan kolom sebagai `meta_data`.

### Lokasi Kode
**File yang salah**: `backend/app/api/agents.py` line 40, 47, 48
```python
reasoning = o.metadata_json.get("reasoning", "No detail available")
# ...
"consensus_score": o.metadata_json.get("consensus_score", 0.0),
"agent_signals": o.metadata_json.get("agent_signals", {})
```

**Model Order** (`backend/app/models/order.py` line 54):
```python
meta_data = Column(JSON, default=dict)  # ← Nama kolom yang benar
```

### Dampak
Endpoint `GET /api/agents/decisions` akan **crash** dengan:
```
AttributeError: 'Order' object has no attribute 'metadata_json'
```

### Solusi
Ganti semua `o.metadata_json` menjadi `o.meta_data` di file `backend/app/api/agents.py`:

```python
# Line 40:
reasoning = o.meta_data.get("reasoning", "No detail available") if o.meta_data else "No detail available"
# Line 47:
"consensus_score": o.meta_data.get("consensus_score", 0.0) if o.meta_data else 0.0,
# Line 48:
"agent_signals": o.meta_data.get("agent_signals", {}) if o.meta_data else {}
```

**Penting:** Tambahkan null check (`if o.meta_data`) karena `meta_data` bisa `None` jika order dibuat tanpa metadata.

### Definition of Done
- [ ] Semua `o.metadata_json` diganti ke `o.meta_data`
- [ ] Null safety ditambahkan untuk `meta_data` yang bisa `None`
- [ ] Endpoint `/api/agents/decisions` bisa diakses tanpa error

---

## Issue #4: 🔴 [BUG] `trades.py` — Route `/stats` tidak bisa diakses karena konflik dengan `/{trade_id}`

**Labels:** `bug`, `priority-high`, `epic-13`

### Deskripsi Bug
Di `backend/app/api/trades.py`, route `GET /{trade_id}` (line 46) didefinisikan **sebelum** `GET /stats` (line 61). FastAPI mencocokkan route secara berurutan (*first match wins*), sehingga:

1. Client request: `GET /api/trades/stats`
2. FastAPI cocokkan dengan `/{trade_id}` → `trade_id = "stats"`
3. Karena `trade_id` diharapkan `int`, terjadi **422 Validation Error**

### Solusi
**Pindahkan** definisi `/stats` ke **ATAS** definisi `/{trade_id}`:

```python
# Urutan yang benar:
@router.get("/stats")         # ← Ini harus PERTAMA
async def get_trade_stats(...):

@router.get("/{trade_id}")    # ← Ini harus KEDUA
async def get_trade_detail(...):
```

**Aturan umum di FastAPI**: Static routes (seperti `/stats`) harus selalu didefinisikan sebelum dynamic routes (seperti `/{trade_id}`).

### Definition of Done
- [ ] Route `/stats` dipindahkan sebelum `/{trade_id}`
- [ ] `GET /api/trades/stats` mengembalikan data statistik
- [ ] `GET /api/trades/123` tetap bisa mengambil detail trade

---

## Issue #5: 🟡 [SECURITY] WebSocket endpoint tidak memiliki autentikasi

**Labels:** `security`, `priority-critical`, `epic-14`

### Deskripsi Vulnerability
Endpoint WebSocket (`/ws`) di `backend/app/api/websocket.py` menerima koneksi dari **siapapun** tanpa memvalidasi JWT token. Semua data portfolio, posisi terbuka, dan alert akan di-broadcast ke semua koneksi aktif — termasuk penyerang.

### Lokasi Kode
**File**: `backend/app/api/websocket.py` line 43-46
```python
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Auth Handshake (Simplified for now, in prod should check token in query/header)
    await manager.connect(websocket)  # ← Langsung accept, tanpa auth!
```

### Dampak
- Penyerang bisa melihat **saldo**, **posisi**, dan **keputusan trading** real-time
- Informasi ini bisa digunakan untuk *front-running* atau *counter-trading*

### Solusi
Tambahkan validasi token sebelum meng-`accept` koneksi:

```python
from jose import jwt, JWTError
from app.core.config import settings

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Ambil token dari query parameter: ws://host/ws?token=xxx
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        username = payload.get("sub")
        if username != settings.ADMIN_USERNAME:
            await websocket.close(code=4003, reason="Unauthorized")
            return
    except JWTError:
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    # Token valid, terima koneksi
    await manager.connect(websocket)
    # ... sisa kode sama
```

### Definition of Done
- [ ] WebSocket menolak koneksi tanpa token valid
- [ ] Frontend mengirim token saat connect ke WebSocket
- [ ] Koneksi tanpa/dengan token salah mendapat close code 4001/4003

---

## Issue #6: 🟡 [SECURITY] Hardcoded default JWT_SECRET di config

**Labels:** `security`, `priority-critical`, `epic-14`

### Deskripsi Vulnerability
Di `backend/app/core/config.py` line 47:
```python
JWT_SECRET: str = "super_secret_fallback_key_change_me"
```

Jika developer/operator deploy tanpa mengatur `.env`, **semua JWT token ditandatangani dengan secret yang diketahui publik** (karena kode ini ada di GitHub). Penyerang bisa membuat token valid sendiri.

### Solusi

#### Opsi A: Gagal saat startup jika secret tidak diset
Tambahkan validasi di `startup_event` di `backend/app/main.py`:

```python
@app.on_event("startup")
async def startup_event():
    if settings.JWT_SECRET == "super_secret_fallback_key_change_me" or len(settings.JWT_SECRET) < 32:
        logger.critical("FATAL: JWT_SECRET not configured or too weak. Set a strong secret in .env")
        raise SystemExit("JWT_SECRET must be configured before running in production.")
```

#### Opsi B: Hapus default value
```python
JWT_SECRET: str = ""  # Wajib diisi di .env
```

### Definition of Done
- [ ] Aplikasi menolak start jika `JWT_SECRET` belum dikonfigurasi
- [ ] Error message yang jelas mengarahkan user ke `.env`
- [ ] `.env.example` sudah memiliki instruksi untuk generate secret

---

## Issue #7: 🟡 [SECURITY] Hardcoded plaintext default password "admin" sebagai backdoor

**Labels:** `security`, `priority-critical`, `epic-14`

### Deskripsi Vulnerability
Di `backend/app/api/auth.py` line 50-56, saat `ADMIN_PASSWORD_HASH` kosong, kode menerima password `"admin"` secara plaintext:

```python
else:
    if form_data.password != "admin":
        raise HTTPException(...)
```

Di production, ini berarti **siapapun bisa login dengan username "admin" dan password "admin"** jika operator lupa mengatur password hash.

### Solusi
Ganti emergency fallback dengan penolakan tegas:

```python
if not settings.ADMIN_PASSWORD_HASH:
    logger.critical("ADMIN_PASSWORD_HASH not configured. Login disabled.")
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="System not configured. Please set ADMIN_PASSWORD_HASH in .env"
    )

if not security.verify_password(form_data.password, settings.ADMIN_PASSWORD_HASH):
    log_audit(db, "login_failed", form_data.username, {"reason": "wrong_password"}, ip_address=request.client.host)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
    )
```

Tambahkan juga **script CLI** untuk generate password hash pertama kali:
```bash
# scripts/generate_password.py
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
password = input("Enter new admin password: ")
print(f"ADMIN_PASSWORD_HASH={pwd_context.hash(password)}")
```

### Definition of Done
- [ ] Tidak ada default password "admin" di kode
- [ ] Login ditolak jika `ADMIN_PASSWORD_HASH` belum diset
- [ ] Script `scripts/generate_password.py` tersedia untuk initial setup
- [ ] Instruksi setup password ada di `DEPLOYMENT.md`

---

## Issue #8: 🟡 [SECURITY] 2FA dilewati sepenuhnya saat `TOTP_SECRET` kosong

**Labels:** `security`, `priority-high`, `epic-14`

### Deskripsi Vulnerability
Di `backend/app/api/auth.py` line 79-88:
```python
if settings.TOTP_SECRET:
    if not security.verify_totp(settings.TOTP_SECRET, request.totp_code):
        raise HTTPException(...)
else:
    pass  # ← 2FA dilewati sepenuhnya!
```

Jika `TOTP_SECRET` tidak dikonfigurasi di `.env`, verifikasi 2FA di-skip dan access token langsung diberikan. Ini menghilangkan perlindungan 2FA.

### Solusi
Tolak verifikasi 2FA jika secret belum diset, ATAU terapkan first-run 2FA setup:

```python
if not settings.TOTP_SECRET:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="2FA not configured. Please run setup script first.",
    )

if not security.verify_totp(settings.TOTP_SECRET, request.totp_code):
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid 2FA code",
    )
```

### Definition of Done
- [ ] 2FA tidak bisa dilewati saat `TOTP_SECRET` kosong
- [ ] Error message yang jelas untuk operator
- [ ] Script setup 2FA tersedia (generate QR code)

---

## Issue #9: 🟡 [SECURITY] Silent failure pada decrypt — API key bisa jadi kosong tanpa peringatan

**Labels:** `security`, `priority-high`, `epic-14`

### Deskripsi Vulnerability
Di `backend/app/core/encryption.py` line 28-33:
```python
def decrypt(ciphertext: str) -> str:
    try:
        # ...
    except Exception:
        return ""  # ← Diam-diam mengembalikan string kosong
```

Jika dekripsi gagal (misal: key berubah, data corrupt), fungsi mengembalikan string kosong (`""`) tanpa logging atau error.

**Dampak**: Bot bisa mengirim request ke exchange dengan API key kosong. Exchange akan menolak tapi bot tidak tahu kenapa. Lebih parah: jika exchange memiliki behavior aneh untuk API key kosong.

### Solusi
```python
def decrypt(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        f = Fernet(_get_key())
        return f.decrypt(ciphertext.encode()).decode()
    except Exception as e:
        logger.critical("decryption_failed", error=str(e),
                       hint="JWT_SECRET may have changed or data is corrupted")
        raise ValueError(f"Failed to decrypt sensitive data: {str(e)}")
```

### Definition of Done
- [ ] Dekripsi yang gagal **raise error** alih-alih return kosong
- [ ] Error di-log dengan level CRITICAL
- [ ] Caller menangkap error dan memberikan feedback yang actionable

---

## Issue #10: 🔵 [REFACTOR] Portfolio summary memuat seluruh order ke memory — perlu SQL aggregation

**Labels:** `refactor`, `performance`, `priority-medium`, `epic-13`

### Deskripsi
Di `backend/app/api/portfolio.py` line 38:
```python
closed_orders = db.query(Order).filter(Order.status == "CLOSED").all()
```

Ini memuat **SEMUA** closed orders ke RAM lalu menghitung win rate dan total PnL di Python. Setelah berbulan-bulan operasi (ribuan order), ini bisa:
- Menghabiskan memori server
- Memperlambat response time
- Membuat endpoint timeout di Docker health check

Masalah yang sama ada di `backend/app/api/trades.py` endpoint `/stats`.

### Solusi
Gunakan SQL aggregation:

```python
from sqlalchemy import func, case

# Win Rate & Total PnL via SQL
stats = db.query(
    func.count(Order.id).label("total"),
    func.count(case((Order.pnl_usd > 0, 1))).label("wins"),
    func.sum(Order.pnl_usd).label("total_pnl")
).filter(Order.status == "CLOSED").first()

total = stats.total or 0
win_rate = (stats.wins / total * 100) if total > 0 else 0.0
total_pnl = stats.total_pnl or 0.0
```

### Definition of Done
- [ ] `portfolio.py` dan `trades.py` menggunakan SQL aggregation
- [ ] Tidak ada `.all()` yang memuat seluruh tabel order
- [ ] Response time < 200ms setelah 10.000 order

---

## Issue #11: 🔵 [REFACTOR] Duplikasi fungsi `get_db` di deps.py dan database.py

**Labels:** `refactor`, `code-quality`, `priority-low`, `epic-1`

### Deskripsi
Dua fungsi `get_db()` identik didefinisikan di:
1. `backend/app/api/deps.py` line 19-25
2. `backend/app/core/database.py` line 25-31

Ini membingungkan — developer tidak tahu harus import dari mana.

### Solusi
1. Hapus `get_db` dari `database.py`
2. Pastikan semua router menggunakan `from app.api.deps import get_db`
3. Atau sebaliknya: gunakan hanya yang di `database.py` dan import di `deps.py`

### Definition of Done
- [ ] Hanya SATU definisi `get_db` yang ada
- [ ] Semua referensi mengarah ke satu lokasi
- [ ] Tidak ada import error setelah refactor

---

## Issue #12: 🔵 [REFACTOR] Ganti `datetime.utcnow()` yang deprecated dengan `datetime.now(timezone.utc)`

**Labels:** `refactor`, `code-quality`, `priority-medium`

### Deskripsi
Python 3.12 menandai `datetime.utcnow()` sebagai deprecated ([PEP 495](https://peps.python.org/pep-0495/)). Kode kita menggunakan ini di banyak tempat:

- `backend/app/core/security.py` line 27, 29
- `backend/app/api/bot.py` line 77
- `backend/app/services/paper_trading.py` line 89
- `backend/app/models/risk_state.py` line 31, 34
- `backend/app/models/order.py` line 48, 49

### Solusi
Buat utility function:
```python
# backend/app/core/utils.py
from datetime import datetime, timezone

def utcnow():
    return datetime.now(timezone.utc)
```

Lalu ganti semua `datetime.utcnow()` dengan `utcnow()` dari utility tersebut.

### Definition of Done
- [ ] Semua `datetime.utcnow()` diganti
- [ ] Tidak ada deprecation warning saat runtime
- [ ] Test memverifikasi timezone aware datetime

---

## Issue #13: 🔵 [REFACTOR] Frontend — Import `cn` di akhir file (konvensi)

**Labels:** `refactor`, `code-quality`, `frontend`, `priority-low`

### Deskripsi
Di `frontend/src/app/trading/page.tsx` line 152-153, import statement berada **di akhir** file setelah komponen:
```tsx
// Line 152-153 (akhir file)
import { cn } from "@/lib/utils"
```

Meski valid di JavaScript/TypeScript (import di-hoist ke atas oleh compiler), ini melanggar konvensi standar dan membingungkan developer lain.

### Solusi
Pindahkan import ke atas file bersama import lainnya (setelah line 15).

### Definition of Done
- [ ] Import `cn` dipindahkan ke bagian atas file
- [ ] Build tetap berhasil tanpa error

---

## Issue #14: 🔵 [REFACTOR] Frontend Dashboard menggunakan hardcoded data — belum terhubung ke API

**Labels:** `refactor`, `priority-high`, `epic-12`, `epic-13`

### Deskripsi
Semua komponen dashboard menggunakan data hardcoded lokal, bukan fetching dari API backend yang sudah siap:

| Komponen | Status | API Endpoint yang Tersedia |
|----------|--------|--------------------------|
| `BotControl.tsx` | Hardcoded state | `GET /api/bot/status`, `POST /api/bot/start` |
| `OverviewCards` | Data dummy | `GET /api/portfolio/summary` |
| `EquityChart` | Data statis | `GET /api/portfolio/equity-history` |
| `PositionsTable` | Array lokal | `GET /api/trades/?status=OPEN` |
| Trade History page | 3 mock trades | `GET /api/trades/` |

### Solusi
Untuk setiap komponen:
1. Tambahkan `fetch()` atau gunakan library seperti `swr` untuk data fetching
2. Tambahkan loading states dan error handling
3. Gunakan token JWT dari auth context untuk header `Authorization: Bearer`

### Contoh implementasi BotControl:
```tsx
"use client"
import { useEffect, useState } from "react"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export function BotControl() {
  const [status, setStatus] = useState(null)
  
  useEffect(() => {
    fetch(`${API_BASE}/api/bot/status`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    .then(res => res.json())
    .then(setStatus)
  }, [])
  // ...
}
```

### Definition of Done
- [ ] Semua komponen dashboard terhubung ke API backend
- [ ] Loading state dan error handling diimplementasikan
- [ ] Data real-time ditampilkan dari database

---

## Issue #15: 🔵 [REFACTOR] `audit_log.py` — `db.commit()` dalam service meng-commit transaksi caller

**Labels:** `refactor`, `bug`, `priority-medium`, `epic-14`

### Deskripsi
Di `backend/app/services/audit_log.py` line 33:
```python
def log_audit(db, action, user, ...):
    entry = AuditLog(...)
    db.add(entry)
    db.commit()  # ← MASALAH: commit transaksi caller juga!
```

**Problem**: Saat `log_audit()` dipanggil dari dalam endpoint yang sedang melakukan operasi DB lain, `db.commit()` juga meng-commit operasi caller yang mungkin belum selesai.

**Contoh worst case** di `bot.py`:
```python
risk_state.system_status = "NORMAL"
db.commit()  # 1. Commit perubahan bot status
log_audit(db, "bot_start", ...)  # 2. Di dalamnya, commit LAGI
```

Lebih buruk lagi: jika `log_audit` gagal dan panggil `db.rollback()`, itu bisa rollback commit caller juga.

### Solusi
Gunakan `db.flush()` alih-alih `db.commit()`, dan biarkan caller yang commit:

```python
def log_audit(db, action, user, ...):
    try:
        entry = AuditLog(...)
        db.add(entry)
        db.flush()  # ← Hanya write ke DB tapi belum commit
    except Exception as e:
        logger.error("audit_log_failed", error=str(e), action=action)
        # JANGAN rollback — biarkan caller yang memutuskan
```

### Definition of Done
- [ ] `log_audit` menggunakan `db.flush()` bukan `db.commit()`
- [ ] Caller bertanggung jawab untuk `commit()`
- [ ] Gagalnya audit log tidak mempengaruhi operasi utama
