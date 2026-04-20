# Epic 6: Top Trader Copy-Trading Engine

---

## T-6.1: Service Fetching Leaderboard Top Trader

**Labels:** `epic-6`, `copy-trading`, `integration`, `priority-high`
**Milestone:** Fase 2 — Brain

### Deskripsi
Membuat service yang mengambil data leaderboard trader terbaik dari exchange. Data ini digunakan untuk mengidentifikasi trader mana yang paling konsisten profitnya sehingga aktivitasnya bisa dijadikan sinyal tambahan.

### Sumber Data
- **Bybit Copy Trading Leaderboard:** https://www.bybit.com/copyTrade
- **Binance Leaderboard:** https://www.binance.com/en/futures-activity/leaderboard

### Langkah-Langkah
1. Buat `backend/app/services/copy_trading/leaderboard.py`
2. Gunakan Exchange API atau web scraping untuk ambil leaderboard
3. Data yang diambil per trader: username/ID, win rate, ROI, PnL, drawdown, jumlah followers, durasi track record
4. Lakukan ranking dan filtering (lihat T-6.2)
5. Simpan leaderboard snapshot ke database (untuk tracking perubahan)
6. Refresh harian via scheduler

### Definition of Done
- [ ] Bisa mengambil data top trader dari exchange
- [ ] Data terstruktur: trader_id, win_rate, roi, pnl, drawdown, followers, track_record_days
- [ ] Data disimpan ke database
- [ ] Refresh otomatis setiap 24 jam

### File yang Dibuat
- `[NEW]` `backend/app/services/copy_trading/__init__.py`
- `[NEW]` `backend/app/services/copy_trading/leaderboard.py`

---

## T-6.2: Filtering Algoritma untuk Top Trader

**Labels:** `epic-6`, `copy-trading`, `logic`, `priority-high`
**Milestone:** Fase 2 — Brain
**Depends On:** T-6.1

### Deskripsi
Tidak semua trader di leaderboard layak di-copy. Banyak yang mendapat ranking tinggi karena keberuntungan atau mengambil risiko terlalu besar. Filter ini memastikan hanya trader berkualitas yang dipilih.

### Kriteria Filter

| Kriteria | Minimum | Mengapa? |
|---|---|---|
| Win Rate | ≥ 65% | Konsistensi minimal |
| Track Record | ≥ 30 hari | Cukup data untuk evaluasi |
| ROI | > 0% (positif) | Harus benar-benar profit |
| Max Drawdown | < 20% | Risk management baik |
| Jumlah Trade | ≥ 50 | Cukup sample size |
| Active Status | Aktif dalam 7 hari terakhir | Masih aktif trading |

### Langkah-Langkah
1. Buat `backend/app/services/copy_trading/trader_filter.py`
2. Implementasi semua kriteria di tabel sebagai filter chainable
3. Dari semua yang lolos filter, ambil top 10 berdasarkan composite score
4. Composite score = (win_rate × 0.3) + (roi × 0.3) + (1 - drawdown) × 0.2 + (track_record_days/365 × 0.2)
5. Re-evaluate weekly: trader yang performanya turun di-drop dari list

### Definition of Done
- [ ] Semua kriteria filter diimplementasi
- [ ] Composite scoring berfungsi
- [ ] Top 10 ter-select berdasarkan score
- [ ] Re-evaluation weekly berfungsi

### File yang Dibuat
- `[NEW]` `backend/app/services/copy_trading/trader_filter.py`

---

## T-6.3: Event Tracker — Monitor Posisi Top Trader

**Labels:** `epic-6`, `copy-trading`, `real-time`, `priority-high`
**Milestone:** Fase 2 — Brain
**Depends On:** T-6.2

### Deskripsi
Memantau aktivitas trading dari top 10 trader yang terpilih secara real-time. Setiap kali mereka membuka atau menutup posisi, kita mendeteksinya.

### Langkah-Langkah
1. Buat `backend/app/services/copy_trading/position_tracker.py`
2. Poll posisi trader secara periodik (setiap 1–5 menit) via exchange API
3. Deteksi perubahan: posisi baru (OPEN) atau posisi ditutup (CLOSE)
4. Setiap event disimpan di database: trader_id, symbol, side, size, entry_price, timestamp, event_type
5. Trigger notification ke Copy Trading Agent saat ada event baru

### Definition of Done
- [ ] Posisi top 10 trader terdeteksi
- [ ] Event OPEN dan CLOSE terdeteksi
- [ ] Event disimpan di database
- [ ] Latency < 5 menit dari aksi trader asli

### File yang Dibuat
- `[NEW]` `backend/app/services/copy_trading/position_tracker.py`
- `[NEW]` `backend/app/models/copy_trade_event.py`

---

## T-6.4: Implementasi Copy Trading Agent

**Labels:** `epic-6`, `agent`, `copy-trading`, `priority-high`
**Milestone:** Fase 2 — Brain
**Depends On:** T-6.3

### Deskripsi
Membuat agent yang mengkonversi aktivitas top trader menjadi sinyal trading. Agent ini tidak langsung mengeksekusi copy — sinyalnya menjadi input tambahan ke Consensus Engine.

### Logic
1. Jika ≥ 3 dari top 10 trader open LONG pada pair yang sama → sinyal BUY, confidence berdasarkan % trader yang agree
2. Jika ≥ 3 dari top 10 trader open SHORT → sinyal SELL
3. Jika sinyal ini sejalan dengan agent lain (Technical juga BUY), confidence di-boost
4. Jika berlawanan, confidence di-reduce

### Langkah-Langkah
1. Buat `backend/app/agents/copy_trader.py`
2. Implementasi `analyze()` yang membaca event terakhir top trader
3. Agregasi: hitung berapa trader yang long/short/neutral pada pair target
4. Hasilkan `AgentSignal` format standar
5. Tambahkan metadata: daftar trader yang mendukung sinyal

### Definition of Done
- [ ] Agent menghasilkan sinyal berdasarkan aktivitas top trader
- [ ] Sinyal masuk ke Consensus Engine sebagai satu suara
- [ ] Metadata menyertakan detail trader yang mendukung

### File yang Dibuat
- `[NEW]` `backend/app/agents/copy_trader.py`

---

## T-6.5: Proportional Sizing Logic

**Labels:** `epic-6`, `copy-trading`, `risk-management`, `priority-medium`
**Milestone:** Fase 2 — Brain

### Deskripsi
Ketika copy trading agent menghasilkan sinyal yang akhirnya dieksekusi, ukuran posisi harus dikonversi proporsional terhadap modal user — bukan copy 1:1 dari trader asli.

### Contoh
- Top trader modal $1,000,000, open BTC/USDT $50,000 (5% dari modal)
- User modal $10,000 → proportional = $500 (5% dari modal user)
- Ditambah safety factor 0.5x → final size = $250 (lebih konservatif)

### Langkah-Langkah
1. Method `calculate_proportional_size(trader_position, trader_balance, user_balance, safety_factor=0.5)`
2. Validasi: ukuran tidak boleh melebihi max_position_size dari Risk Manager
3. Safety factor configurable (default 0.5x = setengah dari proporsi asli)

### Definition of Done
- [ ] Proportional sizing terhitung dengan benar
- [ ] Safety factor diterapkan
- [ ] Tidak melebihi risk limit

---

## T-6.6: Integrasi Copy Trading ke Consensus Engine

**Labels:** `epic-6`, `integration`, `priority-medium`
**Milestone:** Fase 2 — Brain
**Depends On:** T-6.4, T-5.2

### Deskripsi
Menghubungkan output Copy Trading Agent ke Consensus Engine agar sinyalnya diperhitungkan dalam voting.

### Langkah-Langkah
1. Register Copy Trading Agent di Consensus Engine
2. Default weight: 0.15 (lebih kecil dari Technical yang 0.30)
3. Agent scoring juga berlaku (bobot berubah berdasarkan akurasi)

### Definition of Done
- [ ] Copy Trading Agent terdaftar di Consensus Engine
- [ ] Sinyal-nya ikut diperhitungkan dalam weighted voting
- [ ] Scoring/weighting berjalan otomatis

---

## T-6.7: Scheduler Refresh Leaderboard

**Labels:** `epic-6`, `scheduler`, `priority-low`
**Milestone:** Fase 2 — Brain
**Depends On:** T-6.1, T-6.2

### Deskripsi
Otomatisasi refresh leaderboard trader setiap hari. Trader yang performanya turun diganti dengan yang baru.

### Langkah-Langkah
1. Buat CRON job yang berjalan setiap hari pukul 00:00 WIB
2. Fetch leaderboard terbaru
3. Apply filter (T-6.2)
4. Bandingkan dengan top 10 saat ini
5. Log perubahan jika ada trader masuk/keluar dari list
6. Update database

### Definition of Done
- [ ] CRON job berjalan harian
- [ ] Perubahan leaderboard terlog
- [ ] Tracker (T-6.3) otomatis mengikuti trader baru
