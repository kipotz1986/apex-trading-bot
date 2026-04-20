# Epic 12: Real-time Dashboard UI

---

## T-12.1: Setup Next.js Project

**Labels:** `epic-12`, `dashboard`, `setup`, `priority-critical`
**Milestone:** Fase 5 — Interface

### Deskripsi
Inisialisasi project Next.js 15 dengan App Router, TypeScript, Tailwind CSS, dan shadcn/ui untuk membangun dashboard trading yang profesional.

### Langkah-Langkah
```bash
# Masuk ke folder frontend
cd frontend

# Create Next.js project (non-interactive)
npx -y create-next-app@latest ./ \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --import-alias "@/*" \
  --no-turbopack

# Install shadcn/ui
npx -y shadcn@latest init

# Install dependencies tambahan
npm install recharts lightweight-charts socket.io-client next-auth
npm install @tanstack/react-table date-fns lucide-react
```

### Definition of Done
- [ ] Next.js project ready di `/frontend`
- [ ] TypeScript + Tailwind + shadcn/ui terinstall
- [ ] `npm run dev` berjalan tanpa error
- [ ] Basic page tampil di browser

---

## T-12.2: Halaman Login + 2FA

**Labels:** `epic-12`, `dashboard`, `auth`, `priority-critical`
**Milestone:** Fase 5 — Interface

### Deskripsi
Halaman login dengan desain modern dan dark mode. Setelah login password, user diminta kode 2FA (TOTP dari Google Authenticator).

### UI Components
- Input email/username
- Input password
- Input TOTP (6-digit 2FA code)
- Login button
- Error message display
- "Remember me" checkbox (opsional)

### Design Requirements
- Dark mode sebagai default
- Animasi loading saat proses login
- Error shake animation jika gagal
- Responsive (mobile-friendly)

### Definition of Done
- [ ] Halaman login terdesain profesional
- [ ] Login flow: password → 2FA → dashboard
- [ ] Error handling untuk credentials salah
- [ ] JWT token tersimpan setelah login berhasil
- [ ] Redirect ke dashboard setelah auth sukses

---

## T-12.3: Layout Dashboard (Sidebar + Main Content)

**Labels:** `epic-12`, `dashboard`, `ui`, `priority-critical`
**Milestone:** Fase 5 — Interface
**Depends On:** T-12.2

### Deskripsi
Membuat layout utama dashboard dengan sidebar navigation dan area konten utama yang responsif.

### Sidebar Navigation Items
- 📊 **Dashboard** (overview utama)
- 📈 **Trading** (open positions + history)
- 🤖 **AI Agents** (agent scores + decision log)
- 🧠 **Learning** (self-learning metrics)
- 📋 **Backtest** (backtesting results)
- ⚙️ **Settings** (konfigurasi)

### Design Requirements
- Collapsible sidebar (bisa dikecilkan jadi icon-only)
- Dark mode with accent color (blue/green gradient)
- Top bar: bot status indicator (🟢 Running / 🔴 Stopped), current time (WIB)
- Responsive: sidebar jadi hamburger menu di mobile

### Definition of Done
- [ ] Sidebar navigation berfungsi
- [ ] Routing antar halaman berjalan
- [ ] Responsive design (desktop + mobile)
- [ ] Bot status indicator di header

---

## T-12.4: Panel Portfolio Overview (Real-time)

**Labels:** `epic-12`, `dashboard`, `real-time`, `priority-critical`
**Milestone:** Fase 5 — Interface
**Depends On:** T-13.7

### Deskripsi
Card-card yang menampilkan ringkasan portfolio secara real-time: total balance, equity, margin, PnL hari ini. Update via WebSocket.

### Cards
1. **Total Balance** — angka besar + perubahan 24h (% dan USD)
2. **Equity** — nilai portofolio termasuk posisi terbuka
3. **Unrealized PnL** — floating profit/loss dari posisi terbuka
4. **Today's PnL** — hasil trading hari ini
5. **Win Rate** — gauge (speedometer) 0-100%
6. **Total Trades** — jumlah trade sejak bot dimulai

### Design Requirements
- Kartu dengan glassmorphism effect
- Angka hijau untuk profit, merah untuk loss
- Animasi counting saat angka berubah
- Update real-time tanpa page refresh

### Definition of Done
- [ ] 6 cards ditampilkan
- [ ] Data real-time via WebSocket
- [ ] Warna hijau/merah sesuai profit/loss
- [ ] Animasi smooth saat data berubah

---

## T-12.5: PnL Chart (Equity Curve)

**Labels:** `epic-12`, `dashboard`, `visualization`, `priority-high`
**Milestone:** Fase 5 — Interface

### Deskripsi
Grafik garis yang menunjukkan pertumbuhan equity dari waktu ke waktu. User bisa pilih range: 1D, 1W, 1M, 3M, ALL.

### Langkah-Langkah
- Gunakan TradingView Lightweight Charts atau Recharts
- X-axis: waktu, Y-axis: equity value
- Area fill di bawah garis (hijau jika naik, merah jika turun)
- Hover tooltip: tanggal, equity, daily PnL
- Time range selector: 1D, 1W, 1M, 3M, ALL

### Definition of Done
- [ ] Chart menampilkan equity curve
- [ ] Time range selector berfungsi
- [ ] Hover tooltip informatif
- [ ] Responsive

---

## T-12.6: Win Rate Gauge + Statistik Performa

**Labels:** `epic-12`, `dashboard`, `visualization`, `priority-medium`
**Milestone:** Fase 5 — Interface

### Deskripsi
Gauge (speedometer-style) untuk win rate + statistik pendukung (avg win, avg loss, profit factor, dll).

### Definition of Done
- [ ] Gauge win rate visual
- [ ] Statistik lengkap ditampilkan
- [ ] Update per-trade

---

## T-12.7: Tabel Open Positions (Real-time)

**Labels:** `epic-12`, `dashboard`, `real-time`, `priority-critical`
**Milestone:** Fase 5 — Interface

### Deskripsi
Tabel yang menampilkan semua posisi terbuka. Update real-time via WebSocket.

### Kolom Tabel
| Kolom | Contoh |
|---|---|
| Symbol | BTC/USDT |
| Side | LONG 🟢 |
| Size | $500.00 |
| Entry Price | $64,200.00 |
| Current Price | $64,500.00 |
| PnL | +$15.00 (+0.3%) |
| Leverage | 5x |
| SL | $63,500.00 |
| TP | $65,500.00 |
| Duration | 2h 30m |

### Design
- Baris hijau jika profit, merah jika loss
- Animasi flash saat harga berubah
- Badge untuk leverage (`5x` di chip kecil)

### Definition of Done
- [ ] Tabel menampilkan semua posisi terbuka
- [ ] Update real-time
- [ ] Warna coding profit/loss
- [ ] Price flash animation

---

## T-12.8: Tabel Trade History

**Labels:** `epic-12`, `dashboard`, `priority-high`
**Milestone:** Fase 5 — Interface

### Deskripsi
Tabel riwayat seluruh trade yang sudah ditutup. Dengan filter, search, pagination, dan export.

### Features
- Filter: date range, pair, side, win/loss
- Search bar
- Pagination (25 per halaman)
- Export to CSV
- Klik row untuk detail (reasoning AI, agent signals)

### Definition of Done
- [ ] Tabel menampilkan semua closed trades
- [ ] Filter dan search berfungsi
- [ ] Pagination smooth
- [ ] Export CSV berfungsi
- [ ] Detail view saat klik row

---

## T-12.9: Panel Agent Scores & AI Decision Log

**Labels:** `epic-12`, `dashboard`, `ai-core`, `priority-medium`
**Milestone:** Fase 5 — Interface

### Deskripsi
Panel yang menampilkan performa masing-masing agent dan log keputusan AI.

### Agent Scores Display
- Bar chart horizontal: agent name vs accuracy %
- Sparkline: trend skor 7 hari terakhir
- Badge: agent weight saat ini

### Decision Log
- Timeline view: setiap keputusan dari terbaru ke terlama
- Setiap entry: timestamp, symbol, decision, consensus score, agent signals breakdown
- Expandable: klik untuk lihat detail reasoning setiap agent

### Definition of Done
- [ ] Agent scores visual
- [ ] Decision log timeline
- [ ] Detail reasoning bisa di-expand

---

## T-12.10: Panel Self-Learning Progress

**Labels:** `epic-12`, `dashboard`, `self-learning`, `priority-medium`
**Milestone:** Fase 5 — Interface

### Deskripsi
Visualisasi kemajuan self-learning bot: RL training metrics, strategy version timeline, pattern memory stats.

### Components
- **Strategy Timeline:** Garis waktu versi strategi (v1 → v2 → v3...) dengan metrik per versi
- **RL Reward Curve:** Grafik reward dari training (harusnya naik seiring waktu)
- **Pattern Memory Stats:** Jumlah patterns, hit rate, coverage
- **Agent Weight Evolution:** Stacked area chart menunjukkan perubahan bobot agent seiring waktu

### Definition of Done
- [ ] Strategy timeline visual
- [ ] RL reward chart
- [ ] Pattern stats tampil
- [ ] Agent weight evolution chart

---

## T-12.11: Bot Control Panel (Toggle, Mode Switch)

**Labels:** `epic-12`, `dashboard`, `control`, `priority-critical`
**Milestone:** Fase 5 — Interface

### Deskripsi
Panel kontrol utama bot dengan toggle ON/OFF dan mode switch. Ini harus prominent dan mudah diakses.

### Components
- **Main Toggle:** Switch besar ON/OFF dengan animasi + konfirmasi
- **Mode Switch:** Radio button Paper / Live (dengan double confirmation untuk Live)
- **Status Indicator:** Running 🟢 / Paused 🟡 / Stopped 🔴 / Error ⚠️
- **Pair Selection:** Checkbox pair mana yang aktif (BTC/USDT, ETH/USDT, dll)
- **Circuit Breaker Status:** Tampilkan status semua circuit breaker

### Safety
- Switch ke OFF: konfirmasi popup "Apakah Anda yakin ingin menghentikan bot?"
- Switch ke Live: double confirmation + checklist harus pass
- Status change harus instant (< 1 detik)

### Definition of Done
- [ ] Toggle ON/OFF berfungsi secara instan
- [ ] Mode switch Paper/Live dengan confirmation
- [ ] Status indicator real-time
- [ ] Pair selection berfungsi

---

## T-12.12: Settings Page

**Labels:** `epic-12`, `dashboard`, `settings`, `priority-medium`
**Milestone:** Fase 5 — Interface

### Deskripsi
Halaman pengaturan untuk konfigurasi bot.

### Sections
1. **AI Provider:** Pilih provider (dropdown), model, API key (masked)
2. **Risk Parameters:** Daily loss limit %, max drawdown %, max leverage, position size %
3. **Trading Pairs:** Enable/disable pair
4. **Notification Preferences:** Toggle per-trade notification, daily report time
5. **Exchange:** Exchange name, testnet toggle

### Definition of Done
- [ ] Semua settings bisa diubah via UI
- [ ] Perubahan tersimpan dan efektif segera
- [ ] API keys di-mask (hanya tampil 4 karakter terakhir)
- [ ] Validasi input (angka, range)

---

## T-12.13: WebSocket Integration

**Labels:** `epic-12`, `dashboard`, `real-time`, `priority-critical`
**Milestone:** Fase 5 — Interface
**Depends On:** T-13.7

### Deskripsi
Mengintegrasikan WebSocket di frontend untuk menerima data real-time dari backend. Semua panel yang bertanda "real-time" harus menggunakan ini.

### Channels
- `portfolio` → balance, equity, pnl
- `positions` → open positions data
- `ticker` → harga pair aktif
- `bot_status` → status bot (running/paused/error)
- `alerts` → critical notifications

### Langkah-Langkah
1. Buat WebSocket hook: `useWebSocket(channel)`
2. Auto-reconnect jika terputus
3. Connection status indicator di footer dashboard
4. Fallback: polling REST API jika WebSocket gagal

### Definition of Done
- [ ] WebSocket connected dan data streaming
- [ ] Auto-reconnect berfungsi
- [ ] Connection indicator di UI
- [ ] Fallback polling tersedia

---

## T-12.14: Responsive Design (Mobile-Friendly)

**Labels:** `epic-12`, `dashboard`, `responsive`, `priority-medium`
**Milestone:** Fase 5 — Interface

### Deskripsi
Pastikan dashboard bisa diakses dan fungsional di perangkat mobile. Quick check PnL dan bot status harus nyaman di HP.

### Breakpoints
- Desktop: ≥ 1024px — full layout
- Tablet: 768px–1023px — collapsed sidebar, 2 kolom
- Mobile: < 768px — hamburger menu, 1 kolom, stack cards

### Definition of Done
- [ ] Layout responsif di 3 breakpoint
- [ ] Sidebar collapse di mobile
- [ ] Cards ter-stack di mobile
- [ ] Toggle + status accessible di semua ukuran
