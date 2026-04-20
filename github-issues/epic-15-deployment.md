# Epic 15: Deployment & DevOps

---

## T-15.1: Dockerfile untuk Backend (Python/FastAPI)

**Labels:** `epic-15`, `devops`, `docker`, `priority-high`
**Milestone:** Fase 6 — Hardening

### Deskripsi
Membuat Dockerfile yang mengemas seluruh backend menjadi container yang siap deploy.

### Langkah-Langkah

```dockerfile
# backend/Dockerfile

# Stage 1: Build
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Install runtime system deps
RUN apt-get update && apt-get install -y \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# Non-root user (security)
RUN useradd -m appuser
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/health')"

# Start server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
```

### Definition of Done
- [ ] `docker build` berhasil tanpa error
- [ ] Container berjalan dan API accessible
- [ ] Multi-stage build (image kecil)
- [ ] Non-root user
- [ ] Health check berfungsi

### File yang Dibuat
- `[NEW]` `backend/Dockerfile`

---

## T-15.2: Dockerfile untuk Frontend (Next.js)

**Labels:** `epic-15`, `devops`, `docker`, `priority-high`
**Milestone:** Fase 6 — Hardening

### Langkah-Langkah

```dockerfile
# frontend/Dockerfile

# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# Stage 2: Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# Stage 3: Runner
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

CMD ["node", "server.js"]
```

### Definition of Done
- [ ] Build berhasil
- [ ] Container berjalan dan dashboard tampil
- [ ] Multi-stage build
- [ ] Non-root user

### File yang Dibuat
- `[NEW]` `frontend/Dockerfile`

---

## T-15.3: docker-compose.yml Production

**Labels:** `epic-15`, `devops`, `docker`, `priority-critical`
**Milestone:** Fase 6 — Hardening

### Deskripsi
Meng-extend docker-compose development (T-1.3) dengan service backend, frontend, dan reverse proxy untuk production.

### Langkah-Langkah

```yaml
# docker-compose.prod.yml

version: '3.8'

services:
  # === APPLICATION ===
  backend:
    build: ./backend
    container_name: apex-backend
    restart: unless-stopped
    env_file: .env
    ports:
      - "8080:8080"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build: ./frontend
    container_name: apex-frontend
    restart: unless-stopped
    env_file: .env
    ports:
      - "3000:3000"
    depends_on:
      - backend

  # === REVERSE PROXY ===
  caddy:
    image: caddy:2-alpine
    container_name: apex-caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - frontend
      - backend

  # === DATABASE (same as dev, extend dari docker-compose.yml) ===
  postgres:
    # ... (sama seperti T-1.3)
  
  redis:
    # ... (sama seperti T-1.3)
  
  chromadb:
    # ... (sama seperti T-1.3)

volumes:
  postgres_data:
  redis_data:
  chromadb_data:
  caddy_data:
  caddy_config:
```

### Definition of Done
- [ ] `docker-compose -f docker-compose.prod.yml up` berjalan
- [ ] Semua service healthy dan berkomunikasi
- [ ] Reverse proxy (Caddy) menserving frontend dan backend
- [ ] HTTPS otomatis via Caddy

### File yang Dibuat
- `[NEW]` `docker-compose.prod.yml`
- `[NEW]` `docker/Caddyfile`

---

## T-15.4: Health Check Endpoints

**Labels:** `epic-15`, `devops`, `observability`, `priority-high`
**Milestone:** Fase 6 — Hardening

### Deskripsi
Setiap service harus memiliki health check endpoint yang bisa digunakan Docker/load balancer untuk verifikasi.

### Endpoint: `GET /health`
```json
{
    "status": "healthy",
    "version": "1.0.0",
    "uptime_seconds": 86400,
    "dependencies": {
        "database": "connected",
        "redis": "connected",
        "chromadb": "connected",
        "exchange_api": "connected",
        "ai_provider": "connected"
    }
}
```

### Definition of Done
- [ ] Backend `/health` endpoint tersedia
- [ ] Semua dependency di-check
- [ ] Return 200 jika healthy, 503 jika unhealthy
- [ ] Docker health check memanfaatkan endpoint ini

### File yang Dibuat
- `[NEW]` `backend/app/api/health.py`

---

## T-15.5: Graceful Shutdown

**Labels:** `epic-15`, `devops`, `reliability`, `priority-high`
**Milestone:** Fase 6 — Hardening

### Deskripsi
Saat bot di-restart atau container di-stop, proses harus shutdown secara bersih: tutup WebSocket, save state, dan **JANGAN tutup posisi trading** (posisi tetap terbuka di exchange).

### Langkah-Langkah
1. Handle SIGTERM/SIGINT signal
2. Stop accepting new trades
3. Stop WebSocket streams
4. Save current state ke database
5. Close database connections
6. Close exchange API connections
7. Log shutdown event

### ⚠️ PENTING
**TIDAK boleh otomatis menutup posisi saat shutdown.** Posisi tetap open di exchange. Bot hanya perlu me-resume monitoring saat start ulang.

### Definition of Done
- [ ] Graceful shutdown dalam < 10 detik
- [ ] Posisi trading TIDAK ditutup
- [ ] State tersimpan untuk resume
- [ ] Semua connection properly closed

---

## T-15.6: Auto-Restart / Self-Healing

**Labels:** `epic-15`, `devops`, `reliability`, `priority-high`
**Milestone:** Fase 6 — Hardening

### Deskripsi
Jika bot crash, harus otomatis restart. Docker `restart: unless-stopped` menangani ini, tapi perlu tambahan logic untuk resume state setelah restart.

### Langkah-Langkah
1. Docker restart policy: `unless-stopped`
2. Saat start: check database untuk state terakhir sebelum shutdown/crash
3. Resume monitoring posisi yang masih terbuka
4. Alert Telegram jika terjadi unexpected restart
5. Max restart: 5x dalam 10 menit (jika lebih, ada bug serius → stop dan alert)

### Definition of Done
- [ ] Auto-restart berfungsi
- [ ] State ter-resume setelah restart
- [ ] Alert saat unexpected restart
- [ ] Max restart limit enforcement

---

## T-15.7: Database Backup Strategy

**Labels:** `epic-15`, `devops`, `data`, `priority-high`
**Milestone:** Fase 6 — Hardening

### Deskripsi
Automated daily backup untuk PostgreSQL database.

### Langkah-Langkah
1. Buat script backup: `pg_dump` → compressed file
2. CRON job harian pukul 03:00 WIB
3. Retention: simpan 7 hari terakhir, hapus yang lebih lama
4. Opsi: upload ke cloud storage (S3/GCS) untuk off-site backup
5. Test restore secara periodik

### Script Backup
```bash
#!/bin/bash
# docker/backup.sh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
FILENAME="apex_backup_${TIMESTAMP}.sql.gz"

# Create backup
docker exec apex-postgres pg_dump -U apex apex_trading | gzip > "${BACKUP_DIR}/${FILENAME}"

# Remove backups older than 7 days
find ${BACKUP_DIR} -name "apex_backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: ${FILENAME}"
```

### Definition of Done
- [ ] Backup otomatis harian
- [ ] File tercompressed
- [ ] Retention 7 hari
- [ ] Restore tested dan berfungsi

### File yang Dibuat
- `[NEW]` `docker/backup.sh`

---

## T-15.8: Monitoring Setup (Opsional)

**Labels:** `epic-15`, `devops`, `monitoring`, `priority-low`
**Milestone:** Fase 6 — Hardening

### Deskripsi
Setup Prometheus + Grafana untuk monitoring system metrics (CPU, memory, disk, network) dan application metrics (trade count, response time, error rate).

### Langkah-Langkah
1. Tambah Prometheus container di docker-compose
2. Tambah Grafana container
3. Backend expose metrics endpoint `/metrics` (prometheus format)
4. Pre-built Grafana dashboard untuk trading metrics
5. Alert rules: high CPU, low disk, high error rate

### Definition of Done
- [ ] Prometheus scraping metrics
- [ ] Grafana dashboard menampilkan metrics
- [ ] Alert rules terkonfigurasi
- [ ] Accessible via dashboard (link dari main app)

---

## T-15.9: Dokumentasi Deployment Step-by-Step

**Labels:** `epic-15`, `documentation`, `priority-high`
**Milestone:** Fase 6 — Hardening

### Deskripsi
Menulis panduan deployment lengkap yang bisa diikuti oleh siapapun (termasuk junior developer) dari kosong hingga bot berjalan.

### Konten Dokumentasi

```markdown
# Deployment Guide

## Prerequisites
- VPS dengan min 4GB RAM, 2 CPU, 40GB SSD
- Docker & Docker Compose terinstall
- Domain name (opsional, untuk HTTPS)

## Step 1: Clone Repository
## Step 2: Setup Environment (.env)
## Step 3: Start Services (docker-compose up)
## Step 4: Setup Telegram Bot
## Step 5: Configure Exchange API Keys
## Step 6: Setup 2FA for Dashboard
## Step 7: Run Paper Trading (2 minggu minimum)
## Step 8: Evaluate & Switch to Live
## Step 9: Monitor & Maintain

## Troubleshooting
- Bot tidak start
- Exchange API error
- Telegram report tidak terkirim
- Dashboard tidak bisa diakses
```

### Definition of Done
- [ ] Panduan lengkap dari nol
- [ ] Copy-paste friendly (semua command bisa langsung di-run)
- [ ] Troubleshooting section
- [ ] Tested: ikuti langkah dari awal → bot berjalan
