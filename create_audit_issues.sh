#!/bin/bash
# =============================================================================
# APEX Trading Bot — Code Audit Issue Creator
# Membuat 15 issue GitHub berdasarkan hasil code review
# Jalankan: gh auth login (jika belum), lalu: bash create_audit_issues.sh
# =============================================================================

REPO="kipotz1986/apex-trading-bot"

echo "🔍 Creating Code Audit Issues for APEX Trading Bot..."
echo "======================================================"

# --- ISSUE #1: Missing Request import ---
gh issue create --repo "$REPO" \
  --title "[BUG] auth.py — Missing Request import causes NameError on login" \
  --label "bug,priority-critical" \
  --body "## Deskripsi
Fungsi \`login()\` di \`backend/app/api/auth.py\` line 32 menggunakan \`request: Request\` tapi \`Request\` tidak di-import dari \`fastapi\`.

## Dampak
Server **crash** dengan \`NameError\` saat \`POST /api/auth/login\` dipanggil. **Tidak ada user bisa login.**

## Lokasi
\`backend/app/api/auth.py\` line 5 dan 32

## Solusi
Ubah line 5 dari:
\`\`\`python
from fastapi import APIRouter, Depends, HTTPException, status
\`\`\`
menjadi:
\`\`\`python
from fastapi import APIRouter, Depends, HTTPException, status, Request
\`\`\`

## DoD
- [ ] \`Request\` di-import dari \`fastapi\`
- [ ] Login endpoint bisa dipanggil tanpa crash"
echo "✅ Issue #1 created"

# --- ISSUE #2: Broken indentation ---
gh issue create --repo "$REPO" \
  --title "[BUG] auth.py — Broken indentation pada password verification logic" \
  --label "bug,priority-critical" \
  --body "## Deskripsi
Logika verifikasi password di \`backend/app/api/auth.py\` line 43-56 memiliki indentasi rusak. Guard \`if settings.ADMIN_PASSWORD_HASH:\` hilang saat refactoring.

## Dampak
Login **selalu gagal** atau **SyntaxError** tergantung Python version.

## Solusi
Ganti blok line 43-56 dengan:
\`\`\`python
    if settings.ADMIN_PASSWORD_HASH:
        if not security.verify_password(form_data.password, settings.ADMIN_PASSWORD_HASH):
            log_audit(db, \"login_failed\", form_data.username, {\"reason\": \"wrong_password\"}, ip_address=request.client.host)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=\"Incorrect username or password\")
    else:
        if form_data.password != \"admin\":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=\"Incorrect username or password\")
\`\`\`

## DoD
- [ ] Indentasi sejajar dan logis
- [ ] Login berfungsi untuk kedua kasus (hash ada / kosong)"
echo "✅ Issue #2 created"

# --- ISSUE #3: metadata_json vs meta_data ---
gh issue create --repo "$REPO" \
  --title "[BUG] agents.py — AttributeError: metadata_json vs meta_data" \
  --label "bug,priority-critical" \
  --body "## Deskripsi
\`backend/app/api/agents.py\` line 40 mengakses \`o.metadata_json\` tapi model Order mendefinisikan kolom sebagai \`meta_data\`.

## Dampak
\`GET /api/agents/decisions\` **crash** dengan \`AttributeError\`.

## Solusi
Ganti semua \`o.metadata_json\` → \`o.meta_data\` di \`agents.py\` + tambahkan null check:
\`\`\`python
reasoning = o.meta_data.get(\"reasoning\", \"No detail\") if o.meta_data else \"No detail\"
\`\`\`

## DoD
- [ ] Semua \`metadata_json\` diganti ke \`meta_data\`
- [ ] Null safety ditambahkan
- [ ] Endpoint decisions bisa diakses"
echo "✅ Issue #3 created"

# --- ISSUE #4: Route ordering ---
gh issue create --repo "$REPO" \
  --title "[BUG] trades.py — Route /stats tidak bisa diakses karena konflik dengan /{trade_id}" \
  --label "bug,priority-high" \
  --body "## Deskripsi
Di \`backend/app/api/trades.py\`, route \`/{trade_id}\` (line 46) didefinisikan SEBELUM \`/stats\` (line 61). FastAPI mencocokkan first-match, sehingga \`/stats\` diinterpretasi sebagai \`trade_id=\"stats\"\` → 422 error.

## Solusi
Pindahkan \`/stats\` endpoint ke ATAS \`/{trade_id}\`:
\`\`\`python
@router.get(\"/stats\")      # ← PERTAMA
async def get_trade_stats():

@router.get(\"/{trade_id}\")  # ← KEDUA
async def get_trade_detail():
\`\`\`

## DoD
- [ ] \`/stats\` didefinisikan sebelum \`/{trade_id}\`
- [ ] Kedua endpoint berfungsi"
echo "✅ Issue #4 created"

# --- ISSUE #5: WebSocket no auth ---
gh issue create --repo "$REPO" \
  --title "[SECURITY] WebSocket endpoint tidak memiliki autentikasi" \
  --label "security,priority-critical" \
  --body "## Deskripsi
\`/ws\` di \`backend/app/api/websocket.py\` menerima koneksi dari siapapun tanpa JWT validation. Data portfolio dan posisi ter-broadcast ke semua — termasuk penyerang.

## Solusi
Validasi token dari query parameter sebelum \`accept()\`:
\`\`\`python
token = websocket.query_params.get(\"token\")
if not token:
    await websocket.close(code=4001, reason=\"Missing token\")
    return
try:
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
except JWTError:
    await websocket.close(code=4001, reason=\"Invalid token\")
    return
await manager.connect(websocket)
\`\`\`

## DoD
- [ ] WebSocket menolak koneksi tanpa token
- [ ] Frontend mengirim token saat connect
- [ ] Close code 4001 untuk unauthorized"
echo "✅ Issue #5 created"

# --- ISSUE #6: Hardcoded JWT_SECRET ---
gh issue create --repo "$REPO" \
  --title "[SECURITY] Hardcoded default JWT_SECRET di config" \
  --label "security,priority-critical" \
  --body "## Deskripsi
\`config.py\` line 47: default JWT_SECRET = \`\"super_secret_fallback_key_change_me\"\`. Jika deploy tanpa \`.env\`, semua JWT token bisa diforge oleh siapapun yang baca kode.

## Solusi
Tambahkan validasi saat startup:
\`\`\`python
if settings.JWT_SECRET == \"super_secret_fallback_key_change_me\" or len(settings.JWT_SECRET) < 32:
    raise SystemExit(\"FATAL: JWT_SECRET not configured.\")
\`\`\`

## DoD
- [ ] App menolak start tanpa proper JWT_SECRET
- [ ] Error message jelas mengarahkan ke .env"
echo "✅ Issue #6 created"

# --- ISSUE #7: Default password ---
gh issue create --repo "$REPO" \
  --title "[SECURITY] Hardcoded plaintext default password 'admin' sebagai backdoor" \
  --label "security,priority-critical" \
  --body "## Deskripsi
\`auth.py\` line 50-56: jika ADMIN_PASSWORD_HASH kosong, login menerima password \`\"admin\"\` plaintext. Ini backdoor di production.

## Solusi
Tolak login jika ADMIN_PASSWORD_HASH belum diset + buat script generate password:
\`\`\`python
if not settings.ADMIN_PASSWORD_HASH:
    raise HTTPException(status_code=503, detail=\"ADMIN_PASSWORD_HASH not configured\")
\`\`\`

## DoD
- [ ] Tidak ada default password di source code
- [ ] Script \`scripts/generate_password.py\` tersedia
- [ ] Instruksi di DEPLOYMENT.md"
echo "✅ Issue #7 created"

# --- ISSUE #8: 2FA bypass ---
gh issue create --repo "$REPO" \
  --title "[SECURITY] 2FA bypass saat TOTP_SECRET kosong" \
  --label "security,priority-high" \
  --body "## Deskripsi
\`auth.py\` line 85-88: jika \`TOTP_SECRET\` kosong, blok \`else: pass\` membuat 2FA dilewati sepenuhnya. Access token langsung diberikan tanpa verifikasi.

## Solusi
Tolak verify-2fa jika TOTP_SECRET belum dikonfigurasi:
\`\`\`python
if not settings.TOTP_SECRET:
    raise HTTPException(status_code=403, detail=\"2FA not configured. Run setup script.\")
\`\`\`

## DoD
- [ ] 2FA tidak bisa dilewati
- [ ] Script setup 2FA dengan QR code tersedia"
echo "✅ Issue #8 created"

# --- ISSUE #9: Silent decrypt failure ---
gh issue create --repo "$REPO" \
  --title "[SECURITY] Silent failure pada decrypt — API key bisa jadi kosong" \
  --label "security,priority-high" \
  --body "## Deskripsi
\`encryption.py\` line 31-33: saat dekripsi gagal (key changed, data corrupt), return \`\"\"\` tanpa warning. Bot bisa menggunakan API key kosong ke exchange.

## Solusi
\`\`\`python
except Exception as e:
    logger.critical(\"decryption_failed\", error=str(e))
    raise ValueError(f\"Failed to decrypt: {str(e)}\")
\`\`\`

## DoD
- [ ] Dekripsi gagal = raise error
- [ ] Error di-log level CRITICAL
- [ ] Caller menangkap dan feedback actionable"
echo "✅ Issue #9 created"

# --- ISSUE #10: Memory performance ---
gh issue create --repo "$REPO" \
  --title "[REFACTOR] Portfolio summary memuat seluruh order ke memory — perlu SQL aggregation" \
  --label "refactor,performance,priority-medium" \
  --body "## Deskripsi
\`portfolio.py\` line 38 dan \`trades.py\` \`/stats\`: \`.all()\` memuat SEMUA order ke RAM. Ribuan order = OOM.

## Solusi
Gunakan SQL aggregation:
\`\`\`python
from sqlalchemy import func, case
stats = db.query(
    func.count(Order.id).label(\"total\"),
    func.count(case((Order.pnl_usd > 0, 1))).label(\"wins\"),
    func.sum(Order.pnl_usd).label(\"total_pnl\")
).filter(Order.status == \"CLOSED\").first()
\`\`\`

## DoD
- [ ] SQL aggregation digunakan
- [ ] Tidak ada \`.all()\` di portfolio summary atau stats
- [ ] Response time < 200ms"
echo "✅ Issue #10 created"

# --- ISSUE #11: Duplicate get_db ---
gh issue create --repo "$REPO" \
  --title "[REFACTOR] Duplikasi fungsi get_db di deps.py dan database.py" \
  --label "refactor,code-quality,priority-low" \
  --body "## Deskripsi
Dua \`get_db()\` identik di \`deps.py\` dan \`database.py\`. Membingungkan developer.

## Solusi
Hapus salah satu dan gunakan hanya satu lokasi. Rekomendasikan: hapus dari \`database.py\`, gunakan dari \`deps.py\`.

## DoD
- [ ] Hanya SATU definisi \`get_db\`
- [ ] Semua referensi mengarah ke satu lokasi"
echo "✅ Issue #11 created"

# --- ISSUE #12: datetime deprecated ---
gh issue create --repo "$REPO" \
  --title "[REFACTOR] Ganti datetime.utcnow() yang deprecated" \
  --label "refactor,code-quality,priority-medium" \
  --body "## Deskripsi
Python 3.12 menandai \`datetime.utcnow()\` sebagai deprecated. Digunakan di: security.py, bot.py, paper_trading.py, semua models.

## Solusi
Buat utility \`backend/app/core/utils.py\`:
\`\`\`python
from datetime import datetime, timezone
def utcnow():
    return datetime.now(timezone.utc)
\`\`\`
Ganti semua \`datetime.utcnow()\` → \`utcnow()\`.

## DoD
- [ ] Semua \`datetime.utcnow()\` diganti
- [ ] Tidak ada deprecation warning"
echo "✅ Issue #12 created"

# --- ISSUE #13: Import convention ---
gh issue create --repo "$REPO" \
  --title "[REFACTOR] Frontend — Import cn di akhir file melanggar konvensi" \
  --label "refactor,frontend,priority-low" \
  --body "## Deskripsi
\`frontend/src/app/trading/page.tsx\` line 152-153 memiliki import \`cn\` di akhir file setelah komponen. Melanggar konvensi.

## Solusi
Pindahkan \`import { cn } from \"@/lib/utils\"\` ke bagian atas file.

## DoD
- [ ] Import dipindahkan ke atas
- [ ] Build sukses"
echo "✅ Issue #13 created"

# --- ISSUE #14: Frontend hardcoded data ---
gh issue create --repo "$REPO" \
  --title "[REFACTOR] Frontend Dashboard belum terhubung ke API backend — semua data hardcoded" \
  --label "refactor,priority-high,frontend" \
  --body "## Deskripsi
Semua komponen dashboard (BotControl, OverviewCards, EquityChart, PositionsTable, Trade History) menggunakan data hardcoded lokal. API backend sudah siap tapi belum dipanggil.

## Yang perlu diintegrasi
| Komponen | API Endpoint |
|----------|-------------|
| BotControl | \`GET /api/bot/status\`, \`POST /api/bot/start\|stop\` |
| OverviewCards | \`GET /api/portfolio/summary\` |
| EquityChart | \`GET /api/portfolio/equity-history\` |
| Trade History | \`GET /api/trades/\` |
| Positions | \`GET /api/trades/?status=OPEN\` |

## Solusi
Gunakan \`fetch()\` atau \`swr\` dengan JWT token di header \`Authorization: Bearer\`.

## DoD
- [ ] Semua komponen terhubung ke API
- [ ] Loading + error states
- [ ] Data real-time ditampilkan"
echo "✅ Issue #14 created"

# --- ISSUE #15: Audit log commit ---
gh issue create --repo "$REPO" \
  --title "[REFACTOR] audit_log.py — db.commit() meng-commit transaksi caller" \
  --label "refactor,bug,priority-medium" \
  --body "## Deskripsi
\`services/audit_log.py\` line 33: \`db.commit()\` di dalam \`log_audit()\` juga commit transaksi caller yang mungkin belum selesai.

## Solusi
Gunakan \`db.flush()\` alih-alih \`db.commit()\`:
\`\`\`python
db.add(entry)
db.flush()  # write tapi belum commit
\`\`\`
Biarkan caller yang \`commit()\`.

## DoD
- [ ] \`log_audit\` pakai \`flush()\` bukan \`commit()\`
- [ ] Gagalnya audit log tidak rollback operasi utama"
echo "✅ Issue #15 created"

echo ""
echo "======================================================"
echo "✅ Semua 15 issue berhasil dibuat!"
echo "======================================================"
