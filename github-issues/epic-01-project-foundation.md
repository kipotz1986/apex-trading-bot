# Epic 1: Project Foundation & Repository Setup

---

## T-1.1: Inisialisasi Repository Git dengan `.gitignore` Komprehensif

**Labels:** `epic-1`, `setup`, `security`, `priority-critical`
**Milestone:** Fase 1 — Foundation

### Deskripsi
Menyiapkan konfigurasi `.gitignore` yang komprehensif untuk memastikan **tidak ada satupun file sensitif** (API keys, secret tokens, environment config) yang ikut ter-push ke GitHub. Ini adalah langkah keamanan paling fundamental dan harus dilakukan pertama kali sebelum kode apapun ditulis.

### Mengapa Ini Penting?
Jika file seperti `.env` yang berisi API key exchange (Bybit/Binance) bocor ke GitHub, orang lain bisa **mengakses dan menguras seluruh dana di akun exchange Anda**. Ini bukan teori — ini sudah sering terjadi di dunia nyata.

### Langkah-Langkah Implementasi

#### 1. Buat file `.gitignore` di root project
```bash
touch .gitignore
```

#### 2. Isi `.gitignore` dengan rules berikut
```gitignore
# ===========================
# ENVIRONMENT & SECRETS
# ===========================
.env
.env.*
!.env.example
*.pem
*.key
*.cert
secrets/
config/local.*
config/*.secret.*

# ===========================
# PYTHON
# ===========================
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
*.egg-info/
dist/
build/
.eggs/
*.egg
.mypy_cache/
.pytest_cache/
.ruff_cache/
htmlcov/
.coverage
.coverage.*

# ===========================
# NODE.JS / NEXT.JS
# ===========================
node_modules/
.next/
out/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.pnpm-debug.log*

# ===========================
# DATABASE
# ===========================
*.db
*.sqlite3
*.sql.bak
data/postgres/
data/redis/
data/chromadb/

# ===========================
# DOCKER
# ===========================
docker-compose.override.yml

# ===========================
# IDE
# ===========================
.vscode/settings.json
.idea/
*.swp
*.swo
*~
.DS_Store
Thumbs.db

# ===========================
# LOGS
# ===========================
logs/
*.log

# ===========================
# ML / AI MODELS
# ===========================
models/*.pkl
models/*.pt
models/*.h5
*.onnx
```

#### 3. Buat file `.env.example` sebagai template
File ini BOLEH masuk git karena tidak berisi value sensitif apapun — hanya nama variabel sebagai dokumentasi:
```bash
touch .env.example
```

Isi `.env.example`:
```env
# ======================
# AI Provider Config
# ======================
AI_PROVIDER=openai           # openai | google | anthropic | xai
AI_MODEL=gpt-4o              # model name sesuai provider
AI_API_KEY=                   # <-- ISI API KEY DI .env, BUKAN DI SINI
AI_FALLBACK_PROVIDER=google
AI_FALLBACK_MODEL=gemini-2.5-pro
AI_FALLBACK_API_KEY=

# ======================
# Exchange Config
# ======================
EXCHANGE_NAME=bybit           # bybit | binance | okx
EXCHANGE_API_KEY=
EXCHANGE_API_SECRET=
EXCHANGE_TESTNET=true         # true = paper trading, false = live

# ======================
# Database
# ======================
DATABASE_URL=postgresql://apex:password@localhost:5432/apex_trading
REDIS_URL=redis://localhost:6379/0
CHROMADB_HOST=localhost
CHROMADB_PORT=8000

# ======================
# Telegram
# ======================
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# ======================
# Dashboard Auth
# ======================
JWT_SECRET=
NEXTAUTH_SECRET=
NEXTAUTH_URL=http://localhost:3000

# ======================
# App Config
# ======================
APP_ENV=development           # development | production
LOG_LEVEL=INFO
TIMEZONE=Asia/Jakarta
```

#### 4. Verifikasi `.gitignore` berfungsi
```bash
# Buat file .env dummy untuk test
echo "TEST_SECRET=rahasia" > .env

# Cek apakah git mengabaikannya
git status
# .env TIDAK BOLEH muncul di daftar untracked files

# Hapus file test
rm .env
```

### Definition of Done (Kriteria Selesai)
- [ ] File `.gitignore` ada di root project dengan semua rules di atas
- [ ] File `.env.example` ada di root project sebagai template
- [ ] `git status` tidak menunjukkan file `.env` meskipun file tersebut ada
- [ ] Semua rules untuk Python, Node.js, database, IDE, dan ML model tercakup

### File yang Dibuat/Diubah
- `[NEW]` `.gitignore`
- `[NEW]` `.env.example`

---

## T-1.2: Setup Struktur Folder Monorepo

**Labels:** `epic-1`, `setup`, `architecture`, `priority-critical`
**Milestone:** Fase 1 — Foundation

### Deskripsi
Menyiapkan struktur folder monorepo yang terorganisir. Monorepo berarti frontend dan backend ditempatkan dalam satu repository, tapi dipisah dalam folder masing-masing. Ini memudahkan development karena semua kode di satu tempat.

### Langkah-Langkah Implementasi

#### 1. Buat struktur folder
```bash
# Backend (Python/FastAPI)
mkdir -p backend/app/{agents,services,models,schemas,api,core,utils}
mkdir -p backend/tests

# Frontend (Next.js)
# (akan di-generate oleh npx di task T-12.1, cukup buat placeholder)
mkdir -p frontend

# Shared (type definitions, constants)
mkdir -p shared

# Documentation
mkdir -p docs

# Docker configs
mkdir -p docker

# ML Models storage (gitignored)
mkdir -p models

# Logs (gitignored)
mkdir -p logs
```

#### 2. Buat placeholder README di setiap folder utama
```bash
echo "# Backend - Python/FastAPI" > backend/README.md
echo "# Frontend - Next.js Dashboard" > frontend/README.md
echo "# Shared Types & Constants" > shared/README.md
echo "# Documentation" > docs/README.md
```

#### 3. Buat file `__init__.py` untuk Python packages
```bash
touch backend/app/__init__.py
touch backend/app/agents/__init__.py
touch backend/app/services/__init__.py
touch backend/app/models/__init__.py
touch backend/app/schemas/__init__.py
touch backend/app/api/__init__.py
touch backend/app/core/__init__.py
touch backend/app/utils/__init__.py
touch backend/tests/__init__.py
```

#### 4. Struktur akhir yang diharapkan
```
apex-trading-bot/
├── .gitignore
├── .env.example
├── README.md
├── prd.md
├── docker-compose.yml          # (Task T-1.3)
├── backend/
│   ├── README.md
│   ├── requirements.txt         # (akan diisi seiring development)
│   ├── pyproject.toml
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI entrypoint
│   │   ├── agents/              # Multi-agent AI modules
│   │   │   ├── __init__.py
│   │   │   ├── technical.py     # Technical Analyst Agent
│   │   │   ├── fundamental.py   # Fundamental Analyst Agent
│   │   │   ├── sentiment.py     # Sentiment Analyst Agent
│   │   │   ├── risk_manager.py  # Risk Manager Agent
│   │   │   ├── copy_trader.py   # Copy Trading Agent
│   │   │   └── orchestrator.py  # Master Orchestrator
│   │   ├── services/            # Business logic services
│   │   │   ├── __init__.py
│   │   │   ├── exchange.py      # Exchange API integration
│   │   │   ├── market_data.py   # Market data fetching
│   │   │   ├── execution.py     # Order execution engine
│   │   │   ├── learning.py      # Self-learning / RL engine
│   │   │   ├── telegram.py      # Telegram notification
│   │   │   └── scheduler.py     # CRON / scheduled tasks
│   │   ├── models/              # Database ORM models
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── api/                 # REST API route handlers
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── portfolio.py
│   │   │   ├── trades.py
│   │   │   ├── bot_control.py
│   │   │   └── settings.py
│   │   ├── core/                # Core config, security, database
│   │   │   ├── __init__.py
│   │   │   ├── config.py        # Settings from .env
│   │   │   ├── security.py      # JWT, encryption
│   │   │   └── database.py      # DB connection
│   │   └── utils/               # Helper functions
│   └── tests/
│       └── __init__.py
├── frontend/                    # Next.js (setup di Epic 12)
├── shared/
├── docs/
├── docker/
├── models/                      # ML model files (gitignored)
└── logs/                        # Log files (gitignored)
```

### Definition of Done
- [ ] Semua folder sesuai struktur di atas sudah dibuat
- [ ] Semua `__init__.py` sudah ada
- [ ] README placeholder ada di setiap folder utama
- [ ] Bisa menjalankan `find . -type d` dan hasilnya sesuai

### File yang Dibuat
- Seluruh folder structure + `__init__.py` + placeholder README

---

## T-1.3: Setup Docker Compose untuk Development Environment

**Labels:** `epic-1`, `setup`, `devops`, `priority-high`
**Milestone:** Fase 1 — Foundation

### Deskripsi
Membuat konfigurasi `docker-compose.yml` yang menjalankan semua service pendukung (database, cache, vector DB) dalam satu perintah. Ini memastikan setiap developer punya environment yang identik tanpa perlu install PostgreSQL, Redis, dll secara manual di komputer masing-masing.

### Apa itu Docker Compose?
Docker Compose adalah tool yang menjalankan banyak "container" (semacam mini komputer virtual) sekaligus. Jadi daripada install PostgreSQL, Redis, ChromaDB satu per satu, kita tinggal jalankan `docker-compose up` dan semua langsung ready.

### Langkah-Langkah Implementasi

#### 1. Buat file `docker-compose.yml` di root project
```yaml
version: '3.8'

services:
  # ============================================
  # PostgreSQL + TimescaleDB (Database Utama)
  # ============================================
  postgres:
    image: timescale/timescaledb:latest-pg16
    container_name: apex-postgres
    restart: unless-stopped
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: apex
      POSTGRES_PASSWORD: apex_dev_password
      POSTGRES_DB: apex_trading
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U apex -d apex_trading"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ============================================
  # Redis (Cache, Pub/Sub, Task Queue)
  # ============================================
  redis:
    image: redis:7-alpine
    container_name: apex-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ============================================
  # ChromaDB (Vector Database untuk Self-Learning)
  # ============================================
  chromadb:
    image: chromadb/chroma:latest
    container_name: apex-chromadb
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - chromadb_data:/chroma/chroma
    environment:
      ANONYMIZED_TELEMETRY: "false"

volumes:
  postgres_data:
  redis_data:
  chromadb_data:
```

#### 2. Jalankan dan verifikasi
```bash
# Start semua service
docker-compose up -d

# Cek status
docker-compose ps

# Verifikasi PostgreSQL
docker exec apex-postgres pg_isready -U apex
# Expected: /var/run/postgresql:5432 - accepting connections

# Verifikasi Redis
docker exec apex-redis redis-cli ping
# Expected: PONG

# Verifikasi ChromaDB
curl http://localhost:8000/api/v1/heartbeat
# Expected: {"nanosecond heartbeat": ...}

# Stop semua service
docker-compose down

# Stop dan HAPUS semua data (hati-hati!)
docker-compose down -v
```

### Definition of Done
- [ ] `docker-compose.yml` ada di root project
- [ ] `docker-compose up -d` berhasil tanpa error
- [ ] PostgreSQL bisa diakses di `localhost:5432`
- [ ] Redis bisa diakses di `localhost:6379`
- [ ] ChromaDB bisa diakses di `localhost:8000`
- [ ] Health check semua service passing

### File yang Dibuat
- `[NEW]` `docker-compose.yml`

---

## T-1.4: Konfigurasi `.env.example` dan Dokumentasi Environment Variables

**Labels:** `epic-1`, `setup`, `documentation`, `priority-high`
**Milestone:** Fase 1 — Foundation

### Deskripsi
Memastikan file `.env.example` lengkap dan setiap variabel terdokumentasi dengan jelas. File ini sudah dibuat di T-1.1, task ini menambahkan dokumentasi detail di README dan memastikan backend bisa membaca config ini.

### Langkah-Langkah Implementasi

#### 1. Buat `backend/app/core/config.py`
File ini membaca `.env` dan menyediakan config ke seluruh aplikasi:

```python
"""
Application configuration.
Membaca environment variables dari file .env dan menyediakan
typed settings yang bisa diakses di seluruh aplikasi.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Semua konfigurasi aplikasi. Nilai dibaca dari .env file.
    Jika variabel tidak ada di .env, gunakan default yang tertera.
    """

    # === AI Provider ===
    AI_PROVIDER: str = "openai"
    AI_MODEL: str = "gpt-4o"
    AI_API_KEY: str = ""
    AI_FALLBACK_PROVIDER: Optional[str] = None
    AI_FALLBACK_MODEL: Optional[str] = None
    AI_FALLBACK_API_KEY: Optional[str] = None

    # === Exchange ===
    EXCHANGE_NAME: str = "bybit"
    EXCHANGE_API_KEY: str = ""
    EXCHANGE_API_SECRET: str = ""
    EXCHANGE_TESTNET: bool = True  # True = paper trading (aman)

    # === Database ===
    DATABASE_URL: str = "postgresql://apex:apex_dev_password@localhost:5432/apex_trading"
    REDIS_URL: str = "redis://localhost:6379/0"
    CHROMADB_HOST: str = "localhost"
    CHROMADB_PORT: int = 8000

    # === Telegram ===
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # === Auth ===
    JWT_SECRET: str = ""
    NEXTAUTH_SECRET: str = ""
    NEXTAUTH_URL: str = "http://localhost:3000"

    # === App ===
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    TIMEZONE: str = "Asia/Jakarta"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Singleton instance — import ini di mana saja:
# from app.core.config import settings
settings = Settings()
```

#### 2. Update README.md project root
Tambahkan section "Configuration" yang menjelaskan setiap variabel.

#### 3. Verifikasi
```bash
# Copy example ke .env
cp .env.example .env

# Edit .env dan isi value yang diperlukan
# (minimal DATABASE_URL dan REDIS_URL untuk development)
```

### Definition of Done
- [ ] `backend/app/core/config.py` bisa membaca semua variabel dari `.env`
- [ ] Setiap variabel di `.env.example` memiliki penjelasan komentar
- [ ] README.md memiliki section konfigurasi yang menjelaskan setiap variabel
- [ ] Tidak ada secret value yang hardcoded di source code

### File yang Dibuat/Diubah
- `[NEW]` `backend/app/core/config.py`
- `[MODIFY]` `.env.example` (tambah komentar dokumentasi)
- `[MODIFY]` `README.md` (tambah section konfigurasi)

---

## T-1.5: Setup CI/CD Pipeline Dasar via GitHub Actions

**Labels:** `epic-1`, `setup`, `devops`, `priority-medium`
**Milestone:** Fase 1 — Foundation

### Deskripsi
Membuat GitHub Actions workflow yang secara otomatis menjalankan linting (pengecekan format kode), type checking, dan tests setiap kali ada push atau pull request. Ini mencegah kode jelek masuk ke branch `main`.

### Apa itu CI/CD?
CI (Continuous Integration) berarti setiap kali kode di-push ke GitHub, otomatis dilakukan pengecekan:
- Apakah kode ditulis rapi? (linting)
- Apakah tipe data benar? (type checking)
- Apakah test lulus? (testing)

Jika gagal, GitHub akan menampilkan ❌ merah.

### Langkah-Langkah Implementasi

#### 1. Buat folder `.github/workflows`
```bash
mkdir -p .github/workflows
```

#### 2. Buat file `.github/workflows/ci.yml`
```yaml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  # ===================================
  # Backend (Python) Checks
  # ===================================
  backend:
    name: Backend Tests & Lint
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./backend

    services:
      postgres:
        image: timescale/timescaledb:latest-pg16
        env:
          POSTGRES_USER: apex
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: apex_trading_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install ruff mypy pytest pytest-asyncio

      - name: Lint with Ruff
        run: ruff check .

      - name: Type check with MyPy
        run: mypy app/ --ignore-missing-imports

      - name: Run tests
        run: pytest tests/ -v
        env:
          DATABASE_URL: postgresql://apex:test_password@localhost:5432/apex_trading_test
          REDIS_URL: redis://localhost:6379/0
          APP_ENV: test

  # ===================================
  # Frontend (Next.js) Checks
  # ===================================
  frontend:
    name: Frontend Tests & Lint
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./frontend

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npm run lint

      - name: Type check
        run: npm run type-check

      - name: Build
        run: npm run build

  # ===================================
  # Security Check
  # ===================================
  security:
    name: Security Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Check for secrets in code
        run: |
          # Cari pattern yang mencurigakan
          if grep -rn "sk-[a-zA-Z0-9]" --include="*.py" --include="*.ts" --include="*.js" .; then
            echo "❌ POTENTIAL SECRET FOUND IN CODE!"
            exit 1
          fi
          echo "✅ No secrets found in code"
```

### Definition of Done
- [x] Create `feat/ci-setup` branch
- [x] Create `.github/workflows` directory
- [x] Implement `ci.yml` workflow
- [x] Create Pull Request
- [x] File `.github/workflows/ci.yml` ada dan valid (bisa dilihat di tab Actions GitHub)
- [x] Pipeline berjalan otomatis saat push ke `main` atau `develop`
- [x] Pipeline mencakup: lint, type check, test (backend & frontend), security scan
- [x] Secret scan tidak menemukan API key hardcoded

### File yang Dibuat
- `[NEW]` `.github/workflows/ci.yml`

---

## T-1.6: Setup Logging Framework (Structured JSON Logging)

**Labels:** `epic-1`, `setup`, `observability`, `priority-high`
**Milestone:** Fase 1 — Foundation

### Deskripsi
Mengimplementasikan structured logging (format JSON) di seluruh backend. Log JSON memudahkan pencarian, filtering, dan analisis dibanding log text biasa. Setiap log entry harus memiliki timestamp, level, module, dan message.

### Mengapa JSON Logging?
Log text biasa: `2026-04-20 10:30:00 INFO Trade executed BTC/USDT`
Log JSON: `{"timestamp": "2026-04-20T10:30:00Z", "level": "INFO", "module": "execution", "action": "trade_executed", "pair": "BTC/USDT", "side": "BUY", "amount": 0.01}`

JSON jauh lebih mudah di-search, di-filter, dan di-analisis secara programmatic.

### Langkah-Langkah Implementasi

#### 1. Install dependencies
```bash
pip install structlog python-json-logger
```

#### 2. Buat file `backend/app/core/logging.py`
```python
"""
Structured JSON Logging Configuration.

Semua log di aplikasi APEX menggunakan format JSON terstruktur.
Import logger dari sini:
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("trade_executed", pair="BTC/USDT", side="BUY")
"""

import logging
import sys
import structlog
from app.core.config import settings


def setup_logging() -> None:
    """Setup structured logging untuk seluruh aplikasi."""

    # Tentukan log level dari config
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            # Jika development, pakai format berwarna yang mudah dibaca
            # Jika production, pakai format JSON
            structlog.dev.ConsoleRenderer()
            if settings.APP_ENV == "development"
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Dapatkan logger instance untuk module tertentu.
    
    Usage:
        logger = get_logger(__name__)
        logger.info("something_happened", key="value")
        logger.error("something_failed", error=str(e))
    """
    return structlog.get_logger(name)
```

#### 3. Panggil `setup_logging()` di `main.py`
```python
from app.core.logging import setup_logging
setup_logging()
```

#### 4. Contoh penggunaan di seluruh aplikasi
```python
from app.core.logging import get_logger

logger = get_logger(__name__)

# Info level
logger.info("trade_signal_generated",
    pair="BTC/USDT",
    signal="BUY",
    confidence=0.85,
    source="technical_agent"
)

# Warning level
logger.warning("high_drawdown_detected",
    current_drawdown=0.12,
    max_allowed=0.15
)

# Error level
logger.error("exchange_api_error",
    exchange="bybit",
    error="Connection timeout",
    retry_count=3
)
```

### Definition of Done
- [ ] File `backend/app/core/logging.py` sudah ada
- [ ] `setup_logging()` dipanggil saat aplikasi start
- [ ] Log tampil dalam format colorized (development) atau JSON (production)
- [ ] Setiap log entry memiliki: timestamp, level, module name
- [ ] Contoh penggunaan `get_logger()` berfungsi tanpa error

### File yang Dibuat
- `[NEW]` `backend/app/core/logging.py`
- `[MODIFY]` `backend/app/main.py` (tambah `setup_logging()`)
