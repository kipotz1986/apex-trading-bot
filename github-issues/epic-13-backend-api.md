# Epic 13: Backend API & WebSocket Service

---

## T-13.1: REST API — Authentication Endpoints

**Labels:** `epic-13`, `api`, `auth`, `priority-critical`
**Milestone:** Fase 5 — Interface
**Depends On:** Epic 14 (T-14.2, T-14.3)

### Deskripsi
Endpoint untuk login, verifikasi 2FA, dan refresh JWT token.

### Endpoints

| Method | Path | Deskripsi |
|---|---|---|
| `POST` | `/api/auth/login` | Login dengan username + password → return temporary token |
| `POST` | `/api/auth/verify-2fa` | Verifikasi TOTP code → return JWT access + refresh token |
| `POST` | `/api/auth/refresh` | Refresh expired access token dengan refresh token |
| `POST` | `/api/auth/logout` | Invalidate refresh token |
| `GET` | `/api/auth/me` | Get user info dari JWT token |

### Request/Response Examples

#### Login
```json
// POST /api/auth/login
// Request:
{ "username": "admin", "password": "hashed_password" }

// Response (200):
{ "requires_2fa": true, "temp_token": "xxx" }

// Response (401):
{ "error": "Invalid credentials" }
```

#### Verify 2FA
```json
// POST /api/auth/verify-2fa
// Headers: Authorization: Bearer <temp_token>
// Request:
{ "totp_code": "123456" }

// Response (200):
{
    "access_token": "eyJhbGci...",
    "refresh_token": "eyJhbGci...",
    "expires_in": 3600
}
```

### Definition of Done
- [ ] Semua 5 endpoint berfungsi
- [ ] JWT token generation + validation
- [ ] 2FA verification flow
- [ ] Rate limiting pada login endpoint
- [ ] Error responses yang informatif

### File yang Dibuat
- `[NEW]` `backend/app/api/auth.py`

---

## T-13.2: REST API — Portfolio & PnL Data

**Labels:** `epic-13`, `api`, `data`, `priority-critical`
**Milestone:** Fase 5 — Interface

### Endpoints

| Method | Path | Deskripsi |
|---|---|---|
| `GET` | `/api/portfolio/summary` | Balance, equity, PnL summary |
| `GET` | `/api/portfolio/equity-history` | Equity curve data (untuk chart) |
| `GET` | `/api/portfolio/daily-pnl` | PnL harian (untuk chart) |

### Response Example
```json
// GET /api/portfolio/summary
{
    "balance": 10250.00,
    "equity": 10180.00,
    "unrealized_pnl": -70.00,
    "margin_used": 1500.00,
    "free_margin": 8680.00,
    "daily_pnl": 250.00,
    "daily_pnl_pct": 2.5,
    "total_pnl": 1250.00,
    "total_pnl_pct": 13.89,
    "win_rate": 62.5,
    "total_trades": 48
}
```

### Definition of Done
- [ ] Portfolio summary endpoint berfungsi
- [ ] Equity history endpoint (time-series data)
- [ ] Daily PnL endpoint
- [ ] Auth required (JWT)

### File yang Dibuat
- `[NEW]` `backend/app/api/portfolio.py`

---

## T-13.3: REST API — Trade History

**Labels:** `epic-13`, `api`, `data`, `priority-high`
**Milestone:** Fase 5 — Interface

### Endpoints

| Method | Path | Deskripsi |
|---|---|---|
| `GET` | `/api/trades` | List semua closed trades (paginated + filtered) |
| `GET` | `/api/trades/{id}` | Detail 1 trade (termasuk agent signals + reasoning) |
| `GET` | `/api/trades/stats` | Statistik trading (win rate, avg win, sharpe, dll) |

### Query Parameters untuk `GET /api/trades`
- `page` (int, default 1)
- `per_page` (int, default 25, max 100)
- `symbol` (string, filter by pair)
- `side` (string, "buy" atau "sell")
- `result` (string, "win" atau "loss")
- `from_date` (ISO date)
- `to_date` (ISO date)
- `sort` (string, "date" | "pnl" | "duration")
- `order` (string, "asc" | "desc")

### Definition of Done
- [ ] Pagination berfungsi
- [ ] Filter dan sort berfungsi
- [ ] Trade detail menyertakan agent signal breakdown
- [ ] CSV export endpoint (`GET /api/trades/export`)

### File yang Dibuat
- `[NEW]` `backend/app/api/trades.py`

---

## T-13.4: REST API — Bot Control

**Labels:** `epic-13`, `api`, `control`, `priority-critical`
**Milestone:** Fase 5 — Interface

### Endpoints

| Method | Path | Deskripsi |
|---|---|---|
| `GET` | `/api/bot/status` | Status bot (running/paused/stopped/error + detail) |
| `POST` | `/api/bot/start` | Start bot |
| `POST` | `/api/bot/stop` | Stop bot (tidak close positions) |
| `POST` | `/api/bot/mode` | Switch mode (paper/live) — requires double confirm |
| `GET` | `/api/bot/pairs` | List pair aktif |
| `PUT` | `/api/bot/pairs` | Update pair aktif |

### Response `/api/bot/status`
```json
{
    "status": "running",         // running | paused | stopped | error
    "mode": "paper",             // paper | live
    "uptime_seconds": 259200,
    "active_pairs": ["BTC/USDT", "ETH/USDT"],
    "strategy_version": "v3",
    "circuit_breakers": {
        "daily_loss": {"active": false, "current": -1.2, "limit": -3.0},
        "weekly_loss": {"active": false, "current": -2.5, "limit": -7.0},
        "max_drawdown": {"active": false, "current": 5.2, "limit": 15.0},
        "consecutive_losses": {"active": false, "current": 1, "limit": 5}
    },
    "last_error": null
}
```

### Definition of Done
- [ ] Start/stop instant (<1 detik)
- [ ] Mode switch hanya dengan valid confirmation
- [ ] Status endpoint komprehensif
- [ ] Audit log setiap control action

---

## T-13.5: REST API — Settings CRUD

**Labels:** `epic-13`, `api`, `settings`, `priority-medium`
**Milestone:** Fase 5 — Interface

### Endpoints

| Method | Path | Deskripsi |
|---|---|---|
| `GET` | `/api/settings` | Get semua settings |
| `PUT` | `/api/settings` | Update settings |
| `GET` | `/api/settings/ai` | Get AI provider config |
| `PUT` | `/api/settings/ai` | Update AI provider |
| `GET` | `/api/settings/risk` | Get risk parameters |
| `PUT` | `/api/settings/risk` | Update risk parameters |

### Definition of Done
- [ ] Get/update settings berfungsi
- [ ] Validasi input (range, tipe data)
- [ ] Sensitive fields di-mask di response (API keys)
- [ ] Changes applied immediately atau after restart (tergantung setting)

---

## T-13.6: REST API — Agent Scores & Decision Log

**Labels:** `epic-13`, `api`, `ai-core`, `priority-medium`
**Milestone:** Fase 5 — Interface

### Endpoints

| Method | Path | Deskripsi |
|---|---|---|
| `GET` | `/api/agents/scores` | Skor semua agent saat ini |
| `GET` | `/api/agents/scores/history` | Riwayat skor agent (time-series) |
| `GET` | `/api/agents/weights` | Bobot voting saat ini |
| `GET` | `/api/decisions` | Decision log (paginated) |
| `GET` | `/api/decisions/{id}` | Detail keputusan (all agent signals) |
| `GET` | `/api/learning/metrics` | RL training + pattern memory stats |

### Definition of Done
- [ ] Semua endpoint berfungsi
- [ ] Data akurat dan ter-update
- [ ] Pagination pada list endpoints

---

## T-13.7: WebSocket — Real-time Streaming

**Labels:** `epic-13`, `api`, `real-time`, `priority-critical`
**Milestone:** Fase 5 — Interface

### Deskripsi
WebSocket server yang streaming data real-time ke dashboard.

### Channels

```python
# Channel "portfolio" — update setiap 5 detik
{
    "channel": "portfolio",
    "data": {
        "balance": 10250.00,
        "equity": 10180.00,
        "unrealized_pnl": -70.00,
        "daily_pnl": 250.00
    }
}

# Channel "positions" — update saat ada perubahan
{
    "channel": "positions",
    "data": [
        {
            "symbol": "BTC/USDT",
            "side": "buy",
            "size": 500.00,
            "entry_price": 64200.00,
            "current_price": 64500.00,
            "pnl": 15.00,
            "pnl_pct": 0.3
        }
    ]
}

# Channel "bot_status" — update saat status berubah
{
    "channel": "bot_status",
    "data": {
        "status": "running",
        "mode": "paper"
    }
}

# Channel "alerts" — push saat ada alert baru
{
    "channel": "alerts",
    "data": {
        "level": "warning",
        "title": "High Drawdown",
        "message": "Drawdown at 10.5%"
    }
}
```

### Langkah-Langkah
1. Integrasikan WebSocket di FastAPI (`websockets` atau `socket.io`)
2. Implementasi channel subscription (client subscribe ke channel tertentu)
3. Backend broadcast data ke semua connected clients
4. Auth: WebSocket harus authenticated (JWT token di connection handshake)
5. Heartbeat: ping/pong setiap 30 detik untuk menjaga koneksi

### Definition of Done
- [ ] WebSocket server berjalan
- [ ] 4 channels di atas berfungsi
- [ ] Auth required
- [ ] Auto-reconnect dari client side
- [ ] Heartbeat aktif

### File yang Dibuat
- `[NEW]` `backend/app/api/websocket.py`

---

## T-13.8: Rate Limiting & Input Validation

**Labels:** `epic-13`, `api`, `security`, `priority-high`
**Milestone:** Fase 5 — Interface

### Deskripsi
Proteksi semua endpoint dari abuse: rate limiting, input validation, dan sanitization.

### Rules
- Login endpoint: max 5 requests per menit per IP
- API endpoints: max 60 requests per menit per user
- WebSocket: max 10 connections per user
- Input validation: semua body di-validate dengan Pydantic schemas
- SQL injection protection: parameterized queries (handled by ORM)

### Definition of Done
- [ ] Rate limiting aktif
- [ ] Semua input ter-validasi
- [ ] Rate limit exceeded → 429 response
- [ ] Logging suspicious activity

---

## T-13.9: API Documentation (Swagger)

**Labels:** `epic-13`, `api`, `documentation`, `priority-medium`
**Milestone:** Fase 5 — Interface

### Deskripsi
FastAPI otomatis generate dokumentasi Swagger/OpenAPI di `/docs`. Pastikan semua endpoint terdokumentasi dengan baik: deskripsi, request/response examples, auth requirement.

### Langkah-Langkah
1. Tambahkan docstring di setiap endpoint function
2. Gunakan Pydantic models untuk request/response (otomatis muncul di docs)
3. Tag endpoints per group (auth, portfolio, trades, bot, settings)
4. Pastikan `/docs` hanya accessible di development (tidak di production)

### Definition of Done
- [ ] `/docs` menampilkan semua endpoint
- [ ] Setiap endpoint ada deskripsi dan contoh
- [ ] Grouped by tags
- [ ] Disabled di production
