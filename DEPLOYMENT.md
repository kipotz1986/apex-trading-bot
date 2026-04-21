# 🚀 APEX Trading Bot - Deployment Guide

Panduan ini akan membimbing Anda untuk menjalankan **APEX Trading Bot** di server produksi (VPS) menggunakan Docker.

## Persyaratan Minimum
- **OS**: Ubuntu 22.04 LTS atau Linux modern lainnya.
- **Hardware**: Min 4GB RAM, 2 CPU, 40GB SSD.
- **Software**: Docker & Docker Compose terinstal.
- **Akses**: API Keys Bybit/Binance dan Bot Token Telegram.

---

## Langkah 1: Persiapan Environment

1. Clone repository ke server Anda:
   ```bash
   git clone https://github.com/kipotz1986/apex-trading-bot.git
   cd apex-trading-bot
   ```

2. Buat file `.env` dari template:
   ```bash
   cp .env.example .env
   ```

3. Isi variabel penting di `.env`:
   - `JWT_SECRET`: Gunakan string random yang panjang.
   - `EXCHANGE_API_KEY` & `EXCHANGE_API_SECRET`: Kredensial bursa Anda.
   - `TELEGRAM_BOT_TOKEN` & `TELEGRAM_CHAT_ID`: Untuk notifikasi real-time.
   - `DOMAIN`: Domain dashboard Anda (contoh: `bot.domain.com`).
   - `EMAIL`: Email Anda untuk sertifikat SSL Let's Encrypt.

---

## Langkah 1.5: Setup Keamanan (WAJIB)

Sebelum menjalankan bot, Anda harus men-generate secret keys dan password hash yang aman.

### 1. Generate JWT Secret
Gunakan command ini untuk membuat string random 32-byte:
```bash
openssl rand -hex 32
```
Copy hasilnya ke `JWT_SECRET` di `.env`.

### 2. Generate Admin Password Hash
Bot tidak menyimpan password dalam bentuk teks. Gunakan script ini untuk men-generate hash bcrypt:
```bash
python3 -c "from passlib.context import CryptContext; pc=CryptContext(schemes=['bcrypt']); print(pc.hash(input('Masukkan Password: ')))"
```
Copy hasilnya ke `ADMIN_PASSWORD_HASH` di `.env`.

### 3. Generate TOTP Secret (2FA)
Gunakan command ini untuk membuat Base32 secret untuk Google Authenticator/Authy:
```bash
python3 -c "import pyotp; print(pyotp.random_base32())"
```
Copy hasilnya ke `TOTP_SECRET` di `.env`.

### 4. Generate Encryption Key (AES-256)
API Key bursa Anda akan disimpan terenkripsi. Generate key 32-byte:
```bash
python3 -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```
Copy hasilnya ke `ENCRYPTION_KEY` di `.env`.

---

## Langkah 2: Build & Start Services

Jalankan seluruh stack aplikasi menggunakan Docker Compose:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### Langkah 2.5: Jalankan Migrasi Database
Setelah container running, jalankan migrasi untuk membuat tabel:
```bash
docker compose -f docker-compose.prod.yml exec apex-backend alembic upgrade head
```

---
Perintah ini akan secara otomatis:
- Membangun image Backend & Frontend.
- Menjalankan Database, Redis, dan ChromaDB.
- Mengaktifkan **Caddy** untuk HTTPS otomatis.

---

## Langkah 3: Verifikasi Health

Pastikan semua kontainer berjalan dan sistem sehat:
```bash
docker compose -f docker-compose.prod.yml ps
```

Anda juga bisa mengecek endpoint health secara manual:
```bash
curl http://localhost/api/health
```

---

## Langkah 4: Setup Akun Owner (Opsional)

Jika database masih kosong, pastikan Anda telah menyiapkan user admin pertama di sistem untuk bisa login ke Dashboard. 
*Catatan: Dashboard menggunakan 2FA. Pastikan `TOTP_SECRET` telah dikonfigurasi.*

---

## Pemeliharaan (Maintenance)

### Update Bot
Untuk menarik pembaruan kode terbaru:
```bash
git pull origin main
docker compose -f docker-compose.prod.yml up -d --build
```

### Backup Database
Backup dilakukan otomatis via script di `docker/backup.sh`. Anda bisa memasangnya di CRON:
```bash
0 3 * * * /path/to/apex-trading-bot/docker/backup.sh
```

### Shutdown Aman (Graceful)
Untuk mematikan bot tanpa merusak state:
```bash
docker compose -f docker-compose.prod.yml stop
```
*PENTING: Mematikan bot TIDAK akan menutup posisi trading yang sedang terbuka di bursa.*

---

## Troubleshooting
- **Dashboard tidak bisa diakses**: Periksa port 80/443 di firewall.
- **API Error**: Cek log backend dengan `docker logs -f apex-backend`.
- **Database Connection Error**: Pastikan kontainer `apex-postgres` dalam status `healthy`.
