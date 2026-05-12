# Product Requirements Document (PRD)

# APEX Trading Bot — Multi-Agent AI Wealth Advisor

> **Versi:** 2.0
> **Terakhir Diperbarui:** 2026-04-20
> **Status:** Draft — Menunggu Persetujuan

---

## Daftar Isi

1. [Ringkasan Eksekutif](#1-ringkasan-eksekutif)
2. [Latar Belakang & Motivasi](#2-latar-belakang--motivasi)
3. [Tujuan & Sasaran Terukur](#3-tujuan--sasaran-terukur)
4. [Target Platform & Pasar](#4-target-platform--pasar)
5. [Arsitektur Multi-Agent](#5-arsitektur-multi-agent)
6. [Fitur Utama (Lengkap)](#6-fitur-utama-lengkap)
7. [Self-Learning & Reinforcement Learning](#7-self-learning--reinforcement-learning)
8. [Risk Management & Safety Layer](#8-risk-management--safety-layer)
9. [Tech Stack](#9-tech-stack)
10. [Epic & Task List](#10-epic--task-list)
11. [Milestone & Fase Rollout](#11-milestone--fase-rollout)
12. [Glossary (Istilah Trading)](#12-glossary-istilah-trading)

---

## 1. Ringkasan Eksekutif

**APEX** adalah sebuah Trading Bot cerdas yang menggunakan pendekatan **Multi-Agent AI System**. Bot ini bertindak secara otonom sebagai **Wealth Advisor** — menggabungkan beberapa agen AI spesialis yang masing-masing memiliki keahlian berbeda (Analisa Teknikal, Fundamental, Sentimen, Risk Management) untuk berkolaborasi menghasilkan keputusan trading yang optimal.

Yang membedakan APEX dari trading bot konvensional:

- **Self-Learning via Reinforcement Learning (RL):** Bot tidak statis. Ia belajar dari setiap trade yang dilakukan, memperkuat strategi yang berhasil dan melemahkan yang gagal. Setelah 1 bulan operasi, kecerdasannya meningkat secara terukur.
- **Multi-Agent Consensus:** Keputusan trading bukan datang dari 1 model, melainkan hasil "debat" dan voting terbobot antar agen spesialis.
- **Paper Trading First:** Sebelum menyentuh uang sungguhan, seluruh sistem diuji di lingkungan simulasi (Paper Trading / Backtesting).
- **Copy Trading Cerdas:** Tidak sekedar mengikuti, tapi memfilter dan mengadaptasi aktivitas top trader sesuai profil risiko pengguna.

---

## 2. Latar Belakang & Motivasi

Pengguna utama (owner) **tidak memiliki latar belakang trading**. Oleh karena itu, sistem harus:

1. **Sepenuhnya otonom** — Tidak memerlukan intervensi manual untuk analisa maupun eksekusi.
2. **Memiliki safety net berlapis** — Karena owner tidak bisa mengevaluasi keputusan bot secara manual, proteksi kerugian harus sangat ketat dan otomatis.
3. **Transparan dan terdokumentasi** — Setiap keputusan harus bisa di-*trace* alasannya (Explainable AI), sehingga owner bisa memahami "mengapa bot melakukan X".
4. **Self-improving** — Bot harus makin pintar seiring waktu tanpa perlu owner melakukan tuning manual.
5. **Memberikan laporan yang mudah dipahami** — Dalam bahasa yang sederhana, bukan jargon trading.

---

## 3. Tujuan & Sasaran Terukur

| Sasaran | Target Bulan ke-1 | Target Bulan ke-3 |
|---|---|---|
| Win Rate | ≥ 55% | ≥ 65% |
| Maximum Drawdown | < 15% dari total modal | < 10% dari total modal |
| Sharpe Ratio | > 1.0 | > 1.5 |
| Uptime Bot | 99.5% | 99.9% |
| Laporan Harian Terkirim | 100% | 100% |
| Self-Learning Improvement | Baseline ditetapkan | +10% improvement dari baseline |

---

## 4. Target Platform & Pasar

### 4.1 Exchange yang Didukung (Prioritas)
| Exchange | Tipe | Prioritas |
|---|---|---|
| **Bybit** | Crypto Futures & Spot | P0 (Utama) |
| **Binance** | Crypto Futures & Spot | P1 |
| **OKX** | Crypto Futures & Spot | P2 |

### 4.2 Pasangan Aset (Trading Pairs)
- **Fokus Awal:** BTC/USDT, ETH/USDT (pair dengan likuiditas tertinggi)
- **Ekspansi:** Top 10 pair berdasarkan volume 24 jam
- **Filter:** Hanya pair dengan volume harian > $100M untuk menghindari slippage

### 4.3 Tipe Trading
- **Futures (Perpetual Contract)** — Memungkinkan profit dari naik maupun turun harga
- **Leverage:** Default 3x–5x (konservatif), maksimum 10x dengan approval risk agent
- **Timeframe Analisa:** Multi-timeframe (15m, 1H, 4H, 1D)

---

## 5. Arsitektur Multi-Agent

### 5.1 Diagram Agen

```
┌──────────────────────────────────────────────────────────────────┐
│                    MASTER ORCHESTRATOR AGENT                     │
│          (Koordinasi, Consensus Voting, Final Decision)          │
├──────────┬──────────┬──────────┬──────────┬─────────────────────┤
│          │          │          │          │                     │
│  ┌───────▼──────┐ ┌▼────────┐ ┌▼────────┐ ┌▼──────────┐         │
│  │  TECHNICAL   │ │FUNDAMEN-│ │SENTIMENT│ │   RISK    │         │
│  │  ANALYST     │ │TAL      │ │ ANALYST │ │ MANAGER   │         │
│  │  AGENT       │ │ANALYST  │ │  AGENT  │ │  AGENT    │         │
│  │              │ │AGENT    │ │         │ │           │         │
│  │• RSI, MACD   │ │• News   │ │• Social │ │• Position │         │
│  │• Bollinger   │ │• On-Chon│ │• Fear & │ │  Sizing   │         │
│  │• Fibonacci   │ │• Macro  │ │  Greed  │ │• Drawdown │         │
│  │• Volume Prf. │ │• Events │ │• Funding│ │• Circuit  │         │
│  │• Multi-TF    │ │         │ │  Rate   │ │  Breaker  │         │
│  └──────────────┘ └─────────┘ └─────────┘ └───────────┘         │
│          │          │          │          │                     │
│          ▼          ▼          ▼          ▼                     │
│  ┌─────────────────────────────────────────────────────┐        │
│  │              CONSENSUS ENGINE                       │        │
│  │  • Weighted Voting (bobot agent dinamis)            │        │
│  │  • Confidence Threshold (min 70% untuk eksekusi)    │        │
│  │  • Bull vs Bear Debate Protocol                     │        │
│  └───────────────────────┬─────────────────────────────┘        │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────┐        │
│  │              COPY TRADING AGENT                     │        │
│  │  • Validasi sinyal vs top trader activity           │        │
│  │  • Confidence boost jika sinyal selaras             │        │
│  └───────────────────────┬─────────────────────────────┘        │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────┐        │
│  │              EXECUTION ENGINE                       │        │
│  │  • Order Placement (Market/Limit)                   │        │
│  │  • SL/TP Management                                 │        │
│  │  • Position Monitoring                              │        │
│  └─────────────────────────────────────────────────────┘        │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────┐        │
│  │       SELF-LEARNING / RL FEEDBACK ENGINE            │        │
│  │  • Trade Outcome Logging                            │        │
│  │  • Agent Score Update                               │        │
│  │  • Strategy Weight Adjustment                       │        │
│  │  • Pattern Memory Storage (Vector DB)               │        │
│  └─────────────────────────────────────────────────────┘        │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 Peran Setiap Agent

| Agent | Peran | Input | Output |
|---|---|---|---|
| **Technical Analyst** | Analisa pola harga, indikator, level support/resistance | Candlestick data multi-timeframe (15m, 1H, 4H, 1D) | Sinyal: STRONG_BUY / BUY / NEUTRAL / SELL / STRONG_SELL + confidence % |
| **Fundamental Analyst** | Analisa berita, data on-chain, event makroekonomi | News feed, blockchain metrics, economic calendar | Sinyal + reasoning text |
| **Sentiment Analyst** | Analisa mood pasar dari sosial media dan indikator sentimen | Twitter/X, Reddit, Fear & Greed Index, Funding Rate | Sentiment score (-100 s/d +100) |
| **Risk Manager** | Evaluasi kelayakan trade berdasarkan eksposur risiko saat ini | Portfolio state, open positions, account balance | APPROVE / REJECT / REDUCE_SIZE + max position size |
| **Copy Trading Agent** | Pantau dan sinkronisasi aktivitas top trader | Leaderboard API, trader position history | Reinforcement signal + independent trade suggestions |
| **Master Orchestrator** | Menerima semua sinyal, menjalankan consensus, membuat keputusan final | Output semua agent | Final decision: EXECUTE / HOLD + order parameters |

### 5.3 Mekanisme Consensus (Voting Terbobot)

Keputusan trading **bukan** dari satu agen tunggal. Mekanisme:

1. Setiap agent mengeluarkan **sinyal** + **confidence score** (0–100%).
2. Sinyal dikalikan dengan **bobot dinamis** agent tersebut (bobot berubah berdasarkan track record agent).
3. Hasil akhir dihitung: `Final Score = Σ(signal × confidence × agent_weight)`.
4. **Threshold eksekusi:** Trade hanya dieksekusi jika `Final Score ≥ 70%` DAN Risk Manager memberikan `APPROVE`.
5. Jika ada **konflik tajam** antar agent (misal: Technical = STRONG_BUY, Fundamental = STRONG_SELL), Master Orchestrator menjalankan **Debate Protocol** — meminta masing-masing agent menjelaskan alasannya, lalu memutuskan berdasarkan konteks historis.

---

## 6. Fitur Utama (Lengkap)

### 6.1 Analisa Pasar Komprehensif
- **Teknikal Multi-Timeframe:** RSI, MACD, Bollinger Bands, EMA (9, 21, 50, 200), Fibonacci Retracement, Volume Profile, Ichimoku Cloud, ATR.
- **Fundamental:** Berita kripto real-time (CoinDesk, CoinTelegraph), data on-chain (whale movement, exchange inflow/outflow), kalender ekonomi makro.
- **Sentimen:** Fear & Greed Index, Funding Rate, Open Interest, social media buzz score.

### 6.2 Top Trader Copy-Trading Engine
- Monitor **Top 10 Trader** dari leaderboard exchange (Bybit/Binance) berdasarkan:
  - Win Rate ≥ 65%
  - Minimum 30 hari track record
  - ROI positif konsisten
  - Drawdown rendah (< 20%)
- **Smart Copy:** Tidak blindly copy — sinyal dari top trader digunakan sebagai *confirmation signal* yang memperkuat atau melemahkan keputusan consensus engine.
- **Proportional Sizing:** Ukuran posisi dikonversi proporsional terhadap modal pengguna.

### 6.3 Data Persistence & Decision Rationale ("Explainable AI")
Setiap trade yang terjadi menyimpan:
- Snapshot semua sinyal agent + confidence score saat keputusan dibuat
- Reasoning text dari masing-masing agent (mengapa BUY/SELL)
- Market context (harga saat keputusan, volume, indikator kunci)
- Outcome (profit/loss) setelah trade ditutup
- Self-review: evaluasi post-trade apakah keputusan sudah tepat

### 6.4 Professional Auto-Execution
- **Order Types:** Market Order, Limit Order, Stop-Limit
- **Proteksi Otomatis:**
  - Stop Loss (wajib untuk setiap posisi)
  - Take Profit (multi-level: TP1, TP2, TP3 dengan partial close)
  - Trailing Stop (mengunci profit saat harga bergerak favorable)
- **Smart Entry:** Bot menunggu harga optimal (limit order) daripada selalu market order
- **Partial Close:** Menutup sebagian posisi di target profit tertentu untuk mengamankan keuntungan

### 6.5 Daily Telegram Report (Pukul 07:00 WIB)
Laporan harian berisi:
- **Portfolio Summary:** Total balance, total equity, unrealized PnL
- **Kinerja 24 Jam Terakhir:** Jumlah trade, win/loss, net profit
- **Open Positions:** Daftar posisi yang masih terbuka + floating PnL
- **Top Winner & Loser:** Trade terbaik dan terburuk hari itu
- **AI Insight:** Ringkasan singkat dari Master Orchestrator tentang kondisi pasar dan rencana ke depan (dalam bahasa sederhana)
- **Bot Health:** Status sistem (uptime, last error jika ada, RL training progress)

### 6.6 Critical Alert (Real-time, Tidak Hanya Harian)
Selain laporan pagi, bot juga mengirim **alert instan** via Telegram untuk:
- 🔴 **Circuit Breaker Triggered** — Bot berhenti trading otomatis
- 🟡 **Drawdown Warning** — Kerugian mendekati batas
- 🟢 **Big Win** — Profit signifikan tercapai
- 🔵 **Position Opened/Closed** — Notifikasi setiap eksekusi (opsional, bisa di-toggle)
- ⚠️ **System Error** — API disconnect, rate limit, error kritis

### 6.7 Strategy Adaptif & Self-Learning
*(Detail lengkap di Bagian 7)*

### 6.8 Swappable AI Provider
Arsitektur modular mendukung pergantian "otak" AI:

| Provider | Model | Kegunaan |
|---|---|---|
| OpenAI | GPT-4o / GPT-4.1 | General reasoning, trade analysis |
| Google | Gemini 2.5 Pro | Long-context analysis, data processing |
| Anthropic | Claude Opus 4 / Sonnet 4 | Complex reasoning, safety analysis |
| xAI | Grok 3 | Real-time market sentiment |
| Local/Open | Llama 3, Qwen | Fallback, cost optimization |

Konfigurasi via `.env`:
```
AI_PROVIDER=openai
AI_MODEL=gpt-4o
AI_API_KEY=sk-xxx
AI_FALLBACK_PROVIDER=google
AI_FALLBACK_MODEL=gemini-2.5-pro
```

### 6.9 Real-time Web Dashboard
Komponen dashboard:

| Panel | Data | Update |
|---|---|---|
| **Portfolio Overview** | Total Balance, Equity, Margin Used, Free Margin | Real-time (WebSocket) |
| **PnL Chart** | Equity curve harian/mingguan/bulanan | Real-time |
| **Win Rate Gauge** | Persentase win rate keseluruhan dan per-pair | Per-trade update |
| **Open Positions** | Tabel posisi aktif (pair, size, entry, current, PnL, SL, TP) | Real-time |
| **Trade History** | Riwayat seluruh trade + filter & search | On-demand |
| **Agent Scores** | Performa masing-masing agent (accuracy, contribution) | Harian |
| **AI Decision Log** | Reasoning trail setiap keputusan trade | On-demand |
| **Bot Control** | **Toggle ON/OFF**, mode switch (Live/Paper), pair selection | Instant |
| **Settings** | AI Provider config, risk parameters, notification prefs | On-save |
| **Self-Learning Progress** | RL training metrics, strategy evolution timeline | Harian |

### 6.10 Engine Toggle (Kill Switch)
- **Toggle ON/OFF** di dashboard — mengaktifkan/menonaktifkan bot seketika
- **Mode Switch:** Live Trading ↔ Paper Trading
- Saat dimatikan, semua open positions **TIDAK** ditutup otomatis (opsional configurable)
- Status bot realtime terlihat di dashboard (Running / Paused / Error)

### 6.11 Security & Repository Policy
- **Environment Variables:** Semua secrets disimpan di `.env` (TIDAK pernah masuk git)
- **`.gitignore` Ketat:** `.env`, `*.pem`, `*.key`, `secrets/`, `config/local.*`
- **Database Encryption:** API keys exchange dienkripsi dengan AES-256 sebelum disimpan
- **Dashboard Auth:** Login dengan password + 2FA (TOTP via Google Authenticator)
- **Session Management:** JWT dengan expiry + refresh token
- **Rate Limiting:** Proteksi brute force pada endpoint login
- **Audit Log:** Setiap aksi di dashboard dicatat (siapa, kapan, apa)

---

## 7. Self-Learning & Reinforcement Learning

> **Ini adalah fitur pembeda utama APEX.** Bot tidak statis — ia belajar dan berkembang dari setiap pengalaman trading.

### 7.1 Arsitektur Self-Learning

```
┌─────────────────────────────────────────────┐
│           LEARNING PIPELINE                  │
│                                              │
│  ┌──────────┐    ┌──────────┐    ┌────────┐ │
│  │ TRADE    │───▶│ OUTCOME  │───▶│ REWARD │ │
│  │ EXECUTED │    │ RECORDED │    │ CALC   │ │
│  └──────────┘    └──────────┘    └───┬────┘ │
│                                      │      │
│                                      ▼      │
│  ┌──────────┐    ┌──────────┐    ┌────────┐ │
│  │ STRATEGY │◀───│ WEIGHT   │◀───│ AGENT  │ │
│  │ UPDATED  │    │ ADJUSTED │    │ SCORED │ │
│  └──────────┘    └──────────┘    └────────┘ │
│                                      │      │
│                                      ▼      │
│  ┌──────────────────────────────────────┐   │
│  │       PATTERN MEMORY (Vector DB)     │   │
│  │  • Successful trade patterns stored  │   │
│  │  • Failed patterns flagged           │   │
│  │  • Market regime fingerprints        │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

### 7.2 Komponen Self-Learning

#### A. Agent Performance Scoring
Setiap agent memiliki **skor dinamis** yang berubah setelah setiap trade:
- **Skor naik** jika sinyal agent sejalan dengan outcome positif
- **Skor turun** jika sinyal agent menyebabkan kerugian
- Skor ini menentukan **bobot voting** agent di consensus engine
- Contoh: Jika Technical Analyst Agent akurat 80% selama 2 minggu terakhir, bobotnya diperbesar. Jika Sentiment Agent hanya 40%, bobotnya dikecilkan.

#### B. Reinforcement Learning Engine
- **Algoritma:** Proximal Policy Optimization (PPO) atau Twin Delayed DDPG (TD3)
- **State Space:** Gabungan indikator teknikal, sentimen, posisi saat ini, balance
- **Action Space:** BUY / SELL / HOLD / INCREASE / DECREASE position
- **Reward Function:**
  - Profit → reward positif (proporsional terhadap risk-adjusted return)
  - Loss → reward negatif (diperberat jika melanggar risk rules)
  - Menghindari trade buruk (HOLD saat sinyal lemah) → reward kecil positif
- **Training:** Dilakukan secara incremental setiap akhir hari menggunakan data trade hari itu

#### C. Pattern Memory (Long-term Knowledge)
- **Vector Database** (misal: ChromaDB / Qdrant) menyimpan embedding dari:
  - Pola market yang mendahului trade sukses ("fingerprint" kondisi market saat win)
  - Pola market yang mendahului trade gagal (untuk dihindari)
  - Market regime classification (Trending Up / Trending Down / Sideways / High Volatility)
- Saat akan membuat keputusan baru, agent melakukan **similarity search** terhadap pattern memory untuk menemukan situasi historis yang mirip

#### D. Strategy Versioning & Rollback
- Setiap perubahan strategi disimpan sebagai **versi** (v1, v2, v3…)
- Jika strategi baru menghasilkan performa lebih buruk selama 3 hari berturut-turut, sistem **otomatis rollback** ke versi sebelumnya
- Dashboard menampilkan timeline evolusi strategi

#### E. Market Regime Detection
Bot mengenali 4 kondisi pasar dan menyesuaikan perilaku:

| Regime | Ciri-ciri | Perilaku Bot |
|---|---|---|
| **Trending Up** | EMA50 > EMA200, Higher Highs | Agresif Long, trailing stop ketat |
| **Trending Down** | EMA50 < EMA200, Lower Lows | Agresif Short atau cash out |
| **Sideways/Ranging** | Harga di antara support-resistance | Range trading, posisi kecil |
| **High Volatility** | ATR tinggi, news-driven | Sangat konservatif atau pause |

### 7.3 Siklus Pembelajaran 1 Bulan

| Minggu | Fase | Aktivitas |
|---|---|---|
| 1 | **Observasi** | Paper trading, mengumpulkan data baseline, semua agent aktif dengan bobot sama |
| 2 | **Kalibrasi** | Agent scoring dimulai, bobot mulai bergeser, pola pertama tersimpan |
| 3 | **Optimasi** | RL mulai adjust strategy, agent yang buruk di-demote, pattern memory terisi |
| 4 | **Evaluasi** | Perbandingan metrik vs baseline minggu 1, strategy locking untuk yang terbukti |

---

## 8. Risk Management & Safety Layer

> **INI BAGIAN PALING KRITIS.** Tanpa risk management yang ketat, self-learning sekalipun tidak bisa mencegah kehancuran modal.

### 8.1 Circuit Breaker (Pemutus Darurat Otomatis)
Bot **BERHENTI TOTAL** jika salah satu kondisi terpenuhi:

| Trigger | Threshold | Aksi |
|---|---|---|
| **Daily Loss Limit** | Rugi > 3% dari total modal dalam 1 hari | Stop trading 24 jam, kirim alert |
| **Weekly Loss Limit** | Rugi > 7% dari total modal dalam 1 minggu | Stop trading sampai review manual |
| **Max Drawdown** | Equity turun > 15% dari peak | Stop total, tutup semua posisi, kirim alert darurat |
| **Consecutive Losses** | 5 kali rugi berturut-turut | Pause 6 jam, kurangi ukuran posisi 50% |
| **API Error Spike** | > 5 error berturut-turut | Pause trading, kirim alert |

### 8.2 Position Sizing (Money Management)
- **Max posisi tunggal:** 5% dari total modal
- **Max total eksposur:** 20% dari total modal (semua posisi terbuka digabung)
- **Korelasi guard:** Tidak boleh membuka posisi di 2+ pair yang berkorelasi tinggi (misal: BTC & ETH naik turun bersama)
- **Gradual entry:** Posisi besar dipecah menjadi 2-3 entry bertahap (DCA-style)

### 8.3 Validasi Pre-Trade
Sebelum setiap eksekusi, checklist otomatis:
- [ ] Risk Manager Agent approve?
- [ ] Consensus score ≥ threshold?
- [ ] Tidak melanggar daily loss limit?
- [ ] Tidak melanggar max exposure?
- [ ] Saldo cukup (termasuk fee)?
- [ ] Spread/slippage dalam batas wajar?
- [ ] Bukan di waktu event high-impact (opsional)?

### 8.4 Proteksi Tambahan
- **Anti-Liquidation:** Jika margin ratio mendekati level bahaya, posisi diperkecil otomatis
- **Fee-Awareness:** Kalkulasi profit sudah termasuk trading fee + funding fee
- **Slippage Protection:** Market order hanya jika spread < 0.1%, otherwise pakai limit order
- **Cool-down Period:** Setelah trade ditutup (win/loss), tunggu minimum 5 menit sebelum trade baru (mencegah revenge trading)

---

## 9. Tech Stack

### 9.1 Backend
| Komponen | Teknologi | Alasan |
|---|---|---|
| **Runtime** | Python 3.12+ | Ekosistem ML/AI & trading library terlengkap |
| **Framework** | FastAPI | Async, cepat, WebSocket support native |
| **Task Queue** | Celery + Redis | Scheduling, background jobs, CRON |
| **AI Orchestration** | LangGraph / CrewAI | Multi-agent coordination & workflow |
| **RL Training** | Stable-Baselines3 / FinRL | Proven RL framework untuk trading |
| **Exchange SDK** | CCXT (unified) | 1 library untuk semua exchange |

### 9.2 Database
| Tipe | Teknologi | Kegunaan |
|---|---|---|
| **Relational** | PostgreSQL | Trade history, user data, config |
| **Time-Series** | TimescaleDB (ext. PostgreSQL) | Candlestick data, price history |
| **Vector** | ChromaDB / Qdrant | Pattern memory untuk self-learning |
| **Cache** | Redis | Real-time data, session, pub/sub |

### 9.3 Frontend (Dashboard)
| Komponen | Teknologi | Alasan |
|---|---|---|
| **Framework** | Next.js 15 (App Router) | SSR, API routes, React ecosystem |
| **Styling** | Tailwind CSS + shadcn/ui | Rapid UI development, konsisten |
| **Charts** | TradingView Lightweight Charts / Recharts | Profesional trading charts |
| **Real-time** | WebSocket (native) | Streaming data PnL, posisi |
| **Auth** | NextAuth.js + TOTP | Login + 2FA |

### 9.4 Infrastructure
| Komponen | Teknologi |
|---|---|
| **Container** | Docker + docker-compose |
| **Reverse Proxy** | Nginx / Caddy |
| **Monitoring** | Prometheus + Grafana (opsional) |
| **CI/CD** | GitHub Actions |

---

## 10. Epic & Task List

> Daftar ini adalah **acuan utama** untuk seluruh pengembangan project. Setiap task punya ID unik untuk tracking.

---

### Epic 1: Project Foundation & Repository Setup
*Menyiapkan fondasi proyek, struktur, dan keamanan repository.*

- [ ] **T-1.1:** Inisialisasi repository Git dengan `.gitignore` komprehensif (`.env`, `*.pem`, `*.key`, `secrets/`, `__pycache__/`, `node_modules/`, dll.)
- [ ] **T-1.2:** Setup struktur folder monorepo: `/backend` (Python/FastAPI), `/frontend` (Next.js), `/shared` (types/constants), `/docs`
- [ ] **T-1.3:** Setup Docker Compose untuk development environment (PostgreSQL, Redis, TimescaleDB, ChromaDB)
- [ ] **T-1.4:** Konfigurasi `.env.example` sebagai template (tanpa value sensitif) + dokumentasi setiap variable
- [ ] **T-1.5:** Setup CI/CD pipeline dasar (lint, type-check, test) via GitHub Actions
- [ ] **T-1.6:** Setup logging framework (structured JSON logging) untuk seluruh backend service

---

### Epic 2: AI Provider Abstraction Layer
*Membangun lapisan abstraksi agar sistem dapat berganti AI provider tanpa mengubah kode bisnis.*

- [ ] **T-2.1:** Desain interface/abstract class `AIProvider` dengan method standar (`chat`, `analyze`, `embed`)
- [ ] **T-2.2:** Implementasi adapter untuk OpenAI (GPT-4o, GPT-4.1)
- [ ] **T-2.3:** Implementasi adapter untuk Google Gemini (2.5 Pro)
- [ ] **T-2.4:** Implementasi adapter untuk Anthropic Claude (Opus/Sonnet)
- [ ] **T-2.5:** Implementasi adapter fallback (auto-switch jika provider utama error/rate-limited)
- [ ] **T-2.6:** Unit test untuk setiap adapter + integration test fallback mechanism
- [ ] **T-2.7:** Konfigurasi pemilihan provider via `.env` (provider, model, API key, fallback)

---

### Epic 3: Market Data Service
*Mengakuisisi data pasar secara real-time dan historis dari exchange.*

- [ ] **T-3.1:** Integrasi CCXT library untuk koneksi ke Bybit, Binance, OKX
- [ ] **T-3.2:** Service pengambilan data candlestick historis (multi-timeframe: 15m, 1H, 4H, 1D)
- [ ] **T-3.3:** WebSocket stream untuk data harga real-time (ticker, orderbook depth)
- [ ] **T-3.4:** Service pengambilan data on-chain (whale alerts, exchange flow) via API pihak ketiga
- [ ] **T-3.5:** Service pengambilan berita kripto (RSS feed + news API)
- [ ] **T-3.6:** Service pengambilan sentimen (Fear & Greed Index, Funding Rate, Open Interest)
- [ ] **T-3.7:** Penyimpanan data time-series ke TimescaleDB dengan retention policy
- [ ] **T-3.8:** Data normalization layer — memastikan format data konsisten dari berbagai source

---

### Epic 4: Multi-Agent Core — Analyst Agents
*Membangun agen-agen spesialis untuk analisa pasar.*

- [ ] **T-4.1:** Implementasi **Technical Analyst Agent** — kalkulasi indikator (RSI, MACD, Bollinger, EMA, Fibonacci, Volume Profile, ATR, Ichimoku)
- [ ] **T-4.2:** Implementasi multi-timeframe analysis pada Technical Agent (korelasi sinyal antar timeframe)
- [ ] **T-4.3:** Implementasi **Fundamental Analyst Agent** — parsing berita, evaluasi dampak event, data on-chain analysis
- [ ] **T-4.4:** Implementasi **Sentiment Analyst Agent** — agregasi dan scoring sentimen dari multiple source
- [ ] **T-4.5:** Implementasi **Risk Manager Agent** — evaluasi eksposur, position sizing, korelasi antar posisi
- [ ] **T-4.6:** Standarisasi output format semua agent (signal, confidence, reasoning, metadata)
- [ ] **T-4.7:** Prompt engineering & testing untuk setiap agent (optimalkan accuracy)
- [ ] **T-4.8:** Unit test & backtesting masing-masing agent terhadap data historis

---

### Epic 5: Master Orchestrator & Consensus Engine
*Membangun "otak pusat" yang mengkoordinasi semua agent.*

- [ ] **T-5.1:** Implementasi **Master Orchestrator Agent** menggunakan LangGraph/CrewAI
- [ ] **T-5.2:** Implementasi **Consensus Engine** — weighted voting, dynamic threshold
- [ ] **T-5.3:** Implementasi **Debate Protocol** — mekanisme resolusi saat agent berkonflik
- [ ] **T-5.4:** Implementasi dynamic agent weighting — bobot agent berubah berdasarkan track record
- [ ] **T-5.5:** Implementasi **Market Regime Detector** — klasifikasi kondisi pasar (Trending/Sideways/Volatile)
- [ ] **T-5.6:** Implementasi regime-based behavior switching (strategi berubah per regime)
- [ ] **T-5.7:** Integration test — full pipeline dari data masuk hingga keputusan keluar

---

### Epic 6: Top Trader Copy-Trading Engine
*Memantau dan memanfaatkan aktivitas top trader sebagai sinyal tambahan.*

- [ ] **T-6.1:** Service fetching leaderboard top trader dari exchange API (Bybit/Binance)
- [ ] **T-6.2:** Filtering algoritma: Win Rate ≥ 65%, min 30 hari, ROI positif, Drawdown < 20%
- [ ] **T-6.3:** Event tracker — monitor open/close position top trader secara real-time
- [ ] **T-6.4:** Implementasi **Copy Trading Agent** — mengkonversi aktivitas top trader menjadi sinyal
- [ ] **T-6.5:** Proportional sizing logic — konversi ukuran posisi proporsional terhadap modal user
- [ ] **T-6.6:** Integrasi sinyal copy trading ke dalam Consensus Engine (sebagai confirmation signal)
- [ ] **T-6.7:** Scheduler refresh leaderboard (harian) + historical performance tracking

---

### Epic 7: Auto-Execution & Order Management
*Mengeksekusi trade secara otomatis dan aman di exchange.*

- [ ] **T-7.1:** Integrasi CCXT untuk execution (create/cancel/modify order) dengan HMAC signature
- [ ] **T-7.2:** Implementasi order types: Market, Limit, Stop-Limit
- [ ] **T-7.3:** Implementasi otomatis Stop Loss & Take Profit (multi-level TP1/TP2/TP3 dengan partial close)
- [ ] **T-7.4:** Implementasi Trailing Stop logic
- [ ] **T-7.5:** Implementasi **Pre-Trade Validation Checklist** (semua guard dari Risk Management)
- [ ] **T-7.6:** Implementasi Position Monitor — tracking posisi aktif, auto-adjust SL/TP
- [ ] **T-7.7:** Implementasi anti-liquidation guard (reduce position jika margin terlalu rendah)
- [ ] **T-7.8:** Implementasi slippage protection & fee-aware profit calculation
- [ ] **T-7.9:** Implementasi cool-down period antar trade
- [ ] **T-7.10:** Error handling & retry logic untuk API exchange (rate limit, timeout, partial fill)

---

### Epic 8: Risk Management & Circuit Breaker
*Lapisan proteksi untuk mencegah kehancuran modal.*

- [ ] **T-8.1:** Implementasi Daily Loss Limit (stop jika rugi > 3%/hari)
- [ ] **T-8.2:** Implementasi Weekly Loss Limit (stop jika rugi > 7%/minggu)
- [ ] **T-8.3:** Implementasi Max Drawdown Guard (stop total + close all jika drawdown > 15%)
- [ ] **T-8.4:** Implementasi Consecutive Loss Guard (pause setelah 5x rugi berturut)
- [ ] **T-8.5:** Implementasi API Error Spike Detection (pause jika > 5 error berturut)
- [ ] **T-8.6:** Implementasi position sizing rules (max 5% per posisi, max 20% total exposure)
- [ ] **T-8.7:** Implementasi correlation guard (deteksi pair yang berkorelasi tinggi)
- [ ] **T-8.8:** Dashboard display untuk semua risk metrics aktif
- [ ] **T-8.9:** Alert system terintegrasi dengan Telegram untuk semua circuit breaker events

---

### Epic 9: Self-Learning & Reinforcement Learning Engine
*Sistem belajar mandiri agar bot semakin pintar dari waktu ke waktu.*

- [ ] **T-9.1:** Desain reward function untuk RL (profit/loss weighted, risk-adjusted)
- [ ] **T-9.2:** Implementasi state space representation (indikator + posisi + balance → vektor)
- [ ] **T-9.3:** Implementasi RL training pipeline menggunakan Stable-Baselines3 (PPO/TD3)
- [ ] **T-9.4:** Setup ChromaDB/Qdrant sebagai Pattern Memory (Vector Database)
- [ ] **T-9.5:** Implementasi trade outcome embedding — encode pola market saat trade terjadi
- [ ] **T-9.6:** Implementasi similarity search — mencari pola historis yang mirip saat akan trade
- [ ] **T-9.7:** Implementasi Agent Performance Scoring — skor dinamis per agent berdasarkan akurasi
- [ ] **T-9.8:** Implementasi automatic agent weight adjustment berdasarkan score
- [ ] **T-9.9:** Implementasi strategy versioning (v1, v2, v3…) + metadata
- [ ] **T-9.10:** Implementasi auto-rollback — kembali ke versi sebelumnya jika performa turun 3 hari berturut
- [ ] **T-9.11:** Implementasi incremental nightly training (update model setiap malam)
- [ ] **T-9.12:** Metrics & dashboard panel untuk tracking learning progress

---

### Epic 10: Paper Trading & Backtesting
*Lingkungan simulasi untuk menguji bot TANPA risiko kehilangan uang.*

> ⚠️ **WAJIB diselesaikan sebelum Live Trading diaktifkan.**

- [ ] **T-10.1:** Implementasi Paper Trading Engine — simulasi order execution dengan data real-time (tanpa uang sungguhan)
- [ ] **T-10.2:** Implementasi Backtesting Framework — jalankan strategi terhadap data historis (minimal 6 bulan kebelakang)
- [ ] **T-10.3:** Metrik backtesting: Win Rate, Sharpe Ratio, Max Drawdown, Profit Factor, Avg Win/Loss ratio
- [ ] **T-10.4:** Dashboard panel backtesting results dengan visualisasi equity curve
- [ ] **T-10.5:** Mode switch: Paper → Live (dengan konfirmasi double-check)
- [ ] **T-10.6:** Paper trading harus berjalan minimum 2 minggu dengan hasil memuaskan sebelum live

---

### Epic 11: Telegram Notification & Reporting
*Komunikasi otomatis dari bot ke pemilik via Telegram.*

- [ ] **T-11.1:** Setup Telegram Bot via BotFather + konfigurasi token di `.env`
- [ ] **T-11.2:** Implementasi Daily Report Composer — rangkum data 24 jam menjadi pesan terstruktur (Markdown)
- [ ] **T-11.3:** Implementasi Scheduler (CRON) untuk kirim laporan setiap pukul 07:00 WIB
- [ ] **T-11.4:** Implementasi Critical Alert System — kirim alert instan untuk circuit breaker, error, big win
- [ ] **T-11.5:** Implementasi per-trade notification (opsional, bisa di-toggle)
- [ ] **T-11.6:** Implementasi "AI Insight" section — ringkasan kondisi pasar dalam bahasa sederhana
- [ ] **T-11.7:** Implementasi bot health report dalam laporan harian

---

### Epic 12: Real-time Dashboard UI
*Antarmuka visual untuk monitoring dan kontrol bot.*

- [ ] **T-12.1:** Setup Next.js project + Tailwind CSS + shadcn/ui
- [ ] **T-12.2:** Implementasi halaman Login + 2FA (TOTP)
- [ ] **T-12.3:** Implementasi layout utama dashboard (sidebar navigation, responsive)
- [ ] **T-12.4:** Implementasi panel Portfolio Overview (balance, equity, margin, PnL) — real-time via WebSocket
- [ ] **T-12.5:** Implementasi PnL Chart (equity curve) dengan TradingView Lightweight Charts
- [ ] **T-12.6:** Implementasi Win Rate Gauge + statistik performa
- [ ] **T-12.7:** Implementasi tabel Open Positions (real-time update)
- [ ] **T-12.8:** Implementasi tabel Trade History (filter, search, pagination, export)
- [ ] **T-12.9:** Implementasi panel Agent Scores & AI Decision Log
- [ ] **T-12.10:** Implementasi panel Self-Learning Progress (RL metrics, strategy version timeline)
- [ ] **T-12.11:** Implementasi Bot Control Panel (**Toggle ON/OFF**, mode switch Live/Paper, pair selection)
- [ ] **T-12.12:** Implementasi Settings page (AI provider config, risk parameters, notification preferences)
- [ ] **T-12.13:** WebSocket integration untuk semua panel real-time
- [ ] **T-12.14:** Responsive design (mobile-friendly untuk quick check)

---

### Epic 13: Backend API & WebSocket Service
*Endpoint dan streaming data untuk dashboard.*

- [ ] **T-13.1:** REST API: Authentication endpoints (login, verify 2FA, refresh token)
- [ ] **T-13.2:** REST API: Portfolio & PnL data endpoints
- [ ] **T-13.3:** REST API: Trade history endpoints (with pagination, filter)
- [ ] **T-13.4:** REST API: Bot control endpoints (start, stop, switch mode)
- [ ] **T-13.5:** REST API: Settings CRUD endpoints
- [ ] **T-13.6:** REST API: Agent scores & decision log endpoints
- [ ] **T-13.7:** WebSocket: Real-time portfolio, positions, PnL streaming
- [ ] **T-13.8:** Rate limiting & input validation pada semua endpoint
- [ ] **T-13.9:** API documentation (auto-generated via FastAPI/Swagger)

---

### Epic 14: Security Hardening
*Mengamankan seluruh sistem dari kebocoran data dan akses ilegal.*

- [ ] **T-14.1:** Implementasi AES-256 encryption untuk API keys exchange di database
- [ ] **T-14.2:** Implementasi JWT authentication dengan expiry + refresh token rotation
- [ ] **T-14.3:** Implementasi 2FA (TOTP) untuk login dashboard
- [ ] **T-14.4:** Implementasi rate limiting pada endpoint login (anti brute-force)
- [ ] **T-14.5:** Implementasi audit log — catat setiap aksi user di dashboard
- [ ] **T-14.6:** HTTPS enforcement (TLS termination di Nginx/Caddy)
- [ ] **T-14.7:** Review & hardening `.gitignore` — pastikan zero leakage ke repository
- [ ] **T-14.8:** Security scanning (dependency vulnerability check) di CI/CD
- [ ] **T-14.9:** CORS configuration — hanya allow origin yang diizinkan

---

### Epic 15: Deployment & DevOps
*Packaging dan deployment production-ready.*

- [ ] **T-15.1:** Dockerfile untuk backend (Python/FastAPI)
- [ ] **T-15.2:** Dockerfile untuk frontend (Next.js)
- [ ] **T-15.3:** docker-compose.yml (semua service: backend, frontend, PostgreSQL, Redis, TimescaleDB, ChromaDB, Nginx)
- [ ] **T-15.4:** Health check endpoints untuk setiap service
- [ ] **T-15.5:** Implementasi graceful shutdown (tutup posisi tracking saat restart, BUKAN tutup posisi)
- [ ] **T-15.6:** Setup auto-restart / self-healing daemon (restart otomatis jika crash)
- [ ] **T-15.7:** Backup strategy untuk database (automated daily backup)
- [ ] **T-15.8:** Monitoring setup (opsional: Prometheus + Grafana)
- [ ] **T-15.9:** Dokumentasi deployment step-by-step

---

## 11. Milestone & Fase Rollout

| Fase | Durasi | Deliverable | Gate Criteria |
|---|---|---|---|
| **Fase 1: Foundation** | Minggu 1–2 | Epic 1, 2, 3 | Project terstruktur, data mengalir, AI provider bisa dipanggil |
| **Fase 2: Brain** | Minggu 3–5 | Epic 4, 5, 6 | Multi-agent berjalan, consensus menghasilkan sinyal, copy trading aktif |
| **Fase 3: Execution** | Minggu 6–7 | Epic 7, 8, 10 | Paper trading berjalan penuh, risk management aktif, backtesting passed |
| **Fase 4: Intelligence** | Minggu 8–9 | Epic 9 | Self-learning berjalan, agent scoring aktif, pattern memory terisi |
| **Fase 5: Interface** | Minggu 10–11 | Epic 11, 12, 13 | Dashboard live, Telegram report jalan, semua panel berfungsi |
| **Fase 6: Hardening** | Minggu 12 | Epic 14, 15 | Security audit passed, Docker deployed, monitoring aktif |
| **Fase 7: Paper Trial** | Minggu 13–14 | — | 2 minggu paper trading, evaluasi performa, tuning |
| **Fase 8: Go Live** | Minggu 15+ | — | Switch ke Live dengan modal kecil, gradual scaling |

---

## 12. Glossary (Istilah Trading)

> Karena owner tidak memiliki latar belakang trading, berikut penjelasan istilah-istilah yang digunakan dalam dokumen ini.

| Istilah | Penjelasan Sederhana |
|---|---|
| **PnL (Profit and Loss)** | Total keuntungan atau kerugian dari semua perdagangan |
| **Win Rate** | Persentase trade yang menghasilkan profit (misal: 60% artinya 6 dari 10 trade untung) |
| **Drawdown** | Penurunan nilai portofolio dari titik tertinggi ke titik terendah. Drawdown 15% berarti dari Rp100 juta, pernah turun ke Rp85 juta |
| **Sharpe Ratio** | Ukuran kualitas return — makin tinggi makin bagus. > 1.0 = baik, > 2.0 = sangat bagus |
| **Stop Loss (SL)** | Batas harga kerugian maksimal. Jika harga menyentuh titik ini, posisi otomatis ditutup untuk membatasi rugi |
| **Take Profit (TP)** | Batas harga keuntungan target. Jika harga menyentuh titik ini, posisi otomatis ditutup untuk mengamankan profit |
| **Trailing Stop** | Stop Loss yang bergerak mengikuti harga. Jika harga naik, SL ikut naik. Jika harga turun, SL diam di tempat → profit terkunci |
| **Leverage** | "Pinjaman" dari exchange. Leverage 5x berarti modal Rp1 juta bisa trading senilai Rp5 juta. Profit & rugi juga diperbesar 5x |
| **Liquidation** | Jika kerugian melebihi modal (akibat leverage), exchange menutup paksa posisi Anda. Ini harus dihindari |
| **Futures** | Kontrak perdagangan di mana Anda bisa profit baik saat harga naik (Long) maupun turun (Short) |
| **Spot** | Perdagangan langsung — beli aset sungguhan. Hanya bisa profit jika harga naik |
| **Funding Rate** | Biaya periodik yang dibayar/diterima oleh trader Futures. Menunjukkan sentimen pasar |
| **Open Interest** | Total nilai posisi terbuka di pasar. Naik = lebih banyak uang masuk ke pasar |
| **Slippage** | Selisih antara harga yang diharapkan dan harga eksekusi aktual (biasanya terjadi saat pasar bergejolak) |
| **Fear & Greed Index** | Indeks 0–100 yang mengukur sentimen pasar. 0 = sangat takut (biasanya saat harga jatuh), 100 = sangat serakah (biasanya saat harga naik) |
| **EMA (Exponential Moving Average)** | Rata-rata harga yang memberi bobot lebih pada data terbaru. EMA 50 & 200 sering digunakan untuk menentukan tren |
| **RSI (Relative Strength Index)** | Indikator 0–100 yang menunjukkan apakah aset sudah overbought (>70, terlalu mahal) atau oversold (<30, terlalu murah) |
| **MACD** | Indikator yang menunjukkan momentum dan arah tren. Persilangan garis MACD sering menjadi sinyal beli/jual |
| **ATR (Average True Range)** | Ukuran volatilitas (seberapa besar harga bergerak). ATR tinggi = pasar bergejolak |
| **Paper Trading** | Trading simulasi menggunakan uang virtual. Identik dengan live trading tapi tanpa risiko kehilangan uang sungguhan |
| **Backtesting** | Menguji strategi trading pada data historis untuk melihat apakah strategi tersebut menguntungkan di masa lalu |
| **Circuit Breaker** | Mekanisme keamanan yang otomatis menghentikan bot jika kondisi berbahaya terdeteksi (mirip sekring listrik) |
| **DCA (Dollar Cost Averaging)** | Strategi membeli secara bertahap dalam beberapa tahap, bukan sekaligus, untuk mengurangi risiko masuk di harga yang salah |
