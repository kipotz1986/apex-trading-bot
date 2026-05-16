# Audit Sistem APEX Trading Bot — v6
**Tanggal Audit**: 2026-05-11  
**Versi Bot**: V4.2.1-20260510  
**Auditor**: Antigravity AI Agent

---

## Ringkasan Eksekutif

Audit ini mencakup **seluruh jalur data** dari pengambilan data pasar hingga eksekusi order, dengan fokus pada:
1. Data palsu / hardcoded / tidak realistis
2. Perhitungan yang salah secara logika
3. Data yang diambil tapi tidak digunakan
4. Data yang dibutuhkan tapi tidak diambil

**Total temuan**: 12 isu (3 Kritis 🔴, 5 Sedang 🟡, 4 Ringan 🟢)

---

## 🔴 KRITIS — Harus Segera Diperbaiki

### BUG-001: `state_space.py` — Fear & Greed Index Selalu Hardcoded 50

**File**: `backend/app/services/learning/state_space.py` (baris 51)

```python
# KODE SAAT INI (SALAH)
features.append(market_data.get("fear_greed_index", 50) / 100.0)
```

**Masalah**: State vector untuk RL model dan Pattern Memory mengambil `fear_greed_index` dari key yang **tidak pernah ada** di `market_data`. Kunci yang benar adalah `composite_sentiment` (objek `NormalizedSentiment`), bukan `fear_greed_index`.

Akibatnya, feature ini **selalu bernilai `0.5`** (50/100) — data palsu permanen di setiap siklus bot.

**Nilai yang benar harusnya**:
```python
# PERBAIKAN
composite = market_data.get("composite_sentiment")
fng_value = (composite.score + 100) / 200.0 if composite else 0.5  # Normalize -100..100 ke 0..1
features.append(fng_value)
```

**Dampak**: Model RL terlatih dan Pattern Memory selalu menerima sentimen "Neutral 50" tanpa mempertimbangkan kondisi Fear & Greed aktual. State vector tidak akurat → keputusan RL tidak dapat diandalkan.

---

### BUG-002: `agent_scorer.py` — Win Rate Tidak Pernah Dihitung (0% Selamanya)

**File**: `backend/app/services/agent_scorer.py`

**Masalah**: Fungsi `update_performance()` **tidak pernah dipanggil** dari manapun di seluruh codebase. Grepping seluruh project:

```
# Tidak ada pemanggilan update_performance di bot_runner.py, orchestrator.py, atau position_monitor.py
```

Ini berarti:
- `AgentScore.score` tidak pernah diupdate dari nilai awal `100.0`
- `AgentScore.successful_trades` = 0 selamanya
- `AgentScore.total_trades` diupdate di `_persist_decision()` tapi `successful_trades` tidak
- Dashboard menampilkan **0% Win Rate** untuk semua agen — ini adalah **data palsu** karena sistem tidak pernah mengevaluasi apakah prediksi agen benar atau salah

**Bukti di UI**: Screenshot menunjukkan `FUNDAMENTAL: 0%`, `SENTIMENT: 0%`, `TECHNICAL: 0%` — semua nol karena tidak ada mekanisme evaluasi.

**Perbaikan yang diperlukan**: Integrasikan `update_performance()` ke dalam `position_monitor.py` saat posisi ditutup (SL/TP hit atau manual close).

---

### BUG-003: `risk_guard.py` — Kalkulasi Current Exposure Salah

**File**: `backend/app/services/risk/risk_guard.py` (baris 80–84)

```python
# KODE SAAT INI (SALAH)
exposure = self.db.query(Order.requested_amount * Order.average_filled_price).filter(...)
```

**Masalah**: SQLAlchemy tidak secara otomatis mengalikan dua kolom seperti ini dalam query. Query ini akan menghasilkan error atau nilai yang tidak terduga karena `requested_amount` adalah jumlah koin (dalam satuan aset seperti BTC), sedangkan `average_filled_price` adalah harga per koin. Kalkulasi `requested_amount * average_filled_price` **tidak bisa langsung dilakukan di query level SQLAlchemy** tanpa operator eksplisit.

Cara yang benar menggunakan SQLAlchemy:
```python
from sqlalchemy import func
# PERBAIKAN
orders = self.db.query(Order).filter(Order.status == "FILLED", Order.closed_at == None).all()
return sum((o.requested_amount or 0) * (o.average_filled_price or 0) for o in orders)
```

**Dampak**: Batas total exposure tidak terkalkulasi dengan benar → bot mungkin membuka posisi melebihi batas risiko yang ditetapkan.

---

## 🟡 SEDANG — Harus Diperbaiki Segera

### BUG-004: `news_feed.py` — `sentiment_score` Tidak Pernah Diisi

**File**: `backend/app/services/news_feed.py` (baris 62–74)

```python
# KODE SAAT INI
normalized_news.append(NormalizedNews(
    title=item.get("title", ""),
    ...
    # sentiment_score TIDAK DIISI → default 0.0
))
```

**Masalah**: Schema `NormalizedNews` memiliki field `sentiment_score: float` yang menurut definisinya berisi skor sentimen berita dari -1.0 hingga 1.0. Namun `NewsFeedService` tidak pernah mengisinya — selalu `0.0` (default).

CryptoCompare memang tidak menyediakan sentiment score langsung, namun bisa diperkirakan dari field seperti `upvotes`, judul berita, atau kategori.

**Dampak**: Agen Fundamental menerima semua berita dengan sentimen "netral" (0.0) terlepas dari konten aktualnya.

---

### BUG-005: `orchestrator.py` — `current_price` Bisa Bernilai `0.0`

**File**: `backend/app/agents/orchestrator.py` (baris 221)

```python
# KODE SAAT INI
current_price = regime_candles[-1].close if regime_candles else 0.0
```

**Masalah**: Jika `regime_candles` ada tapi candle terakhir memiliki `close = 0.0` (edge case pada data corrupt), maka `asset_amount = size_usd / 0` → **ZeroDivisionError**. Meskipun sudah ada guard `if current_price > 0`, tapi nilai `0.0` bisa muncul dari data yang tidak bersih.

Selain itu, jika `regime_candles` ada tetapi elemen pertamanya tidak memiliki atribut `close` (karena format dict/object), ini akan crash.

---

### BUG-006: `consensus.py` — `proposed_size` Hardcoded $100

**File**: `backend/app/services/consensus.py` (baris 114)

```python
# KODE SAAT INI (DATA PALSU)
"proposed_size": 100.0,  # Default size, will be refined by Risk Manager
```

**Masalah**: Nilai `proposed_size = 100.0` adalah hardcoded placeholder yang diteruskan ke Risk Manager dan RegimeStrategy. Nilai ini **tidak mencerminkan modal aktual** pengguna. 

Akibatnya, ketika `regime_strategy.adjust_decision()` mengalikan `proposed_size * max_size_mult` (misal 0.25 untuk high_volatility), hasilnya adalah `$25` — bukan persentase dari ekuitas sesungguhnya.

**Cara yang benar**: `proposed_size` harus dihitung sebagai persentase dari ekuitas aktual portfolio.

---

### BUG-007: `fundamental.py` — `onchain_summary` Bisa `None`, Tidak Ada Safeguard

**File**: `backend/app/agents/fundamental.py` (baris 52)

```python
# KODE SAAT INI
data_str += f"\nOn-Chain Summary:\n{onchain_summary.model_dump()}\n"
```

**Masalah**: Jika `onchain_summary` adalah `None` (karena fetch gagal dengan default `None` di `bot_runner.py`), pemanggilan `.model_dump()` akan menghasilkan `AttributeError: 'NoneType' object has no attribute 'model_dump'`.

Ini adalah ticking time bomb — jika koneksi ke CoinGecko atau Blockchain.com gagal, seluruh Fundamental Agent akan crash.

---

### BUG-008: `technical.py` — Instruksi Prompt Masih Ada Perintah Lama

**File**: `backend/app/agents/technical.py` (baris 165)

```python
# KODE SAAT INI
instruction = (
    f"...Produce a JSON trading signal. If alignment is true, boost confidence."
)
```

**Masalah**: Instruksi `"If alignment is true, boost confidence"` masih ada di dalam **kode Python** (instruction string), meskipun kita sudah memperbaiki file prompt `.txt`. Instruksi hardcoded ini **override** prompt yang sudah diperbaiki dan masih memaksa LLM untuk selalu memberikan confidence tinggi jika aligned.

---

## 🟢 RINGAN — Perlu Diperhatikan

### BUG-009: `paper_trading.py` — `is_testnet` Hardcoded `False`

**File**: `backend/app/services/paper_trading.py` (baris 64)

```python
is_testnet=False,  # Hardcoded, tidak dinamis
```

Nilai ini seharusnya mengikuti konfigurasi sistem, bukan hardcoded.

---

### BUG-010: `state_space.py` — Feature Dimensions Tidak Konsisten

**File**: `backend/app/services/learning/state_space.py`

Vector dibangun dengan:
- 5 price changes + 1 F&G + 3 portfolio + 6 agent signals + 1 volatility = **16 features**
- Tapi `feature_dim=25` → **9 fitur adalah padding nol**

Padding permanen seperti ini membuang kapasitas representasi model RL. Lebih baik menambahkan fitur bermakna seperti volume, OI, hash rate.

---

### BUG-011: `onchain_data.py` — `avg_block_size` Mengambil Key yang Salah

**File**: `backend/app/services/onchain_data.py` (baris 137)

```python
"avg_block_size": data.get("blocks_avg", 0),  # Key yang salah
```

Response API Blockchain.com untuk field blok adalah `"avg_block_size"`, bukan `"blocks_avg"`. Nilai ini selalu `0` akibat key mismatch.

---

### BUG-012: `regime_strategy.py` — Confidence Tidak Dinormalisasi Sebelum Dibandingkan

**File**: `backend/app/services/regime_strategy.py` (baris 60)

```python
if decision["confidence"] < params["min_confidence"]:
```

**Masalah**: `decision["confidence"]` dari `consensus.py` adalah `abs(total_score)` (antara 0.0 dan 1.0). Namun setelah RL model atau Pattern Memory menambahkan `+0.1`, nilai ini bisa melebihi 1.0 tanpa di-clamp, sehingga perbandingan `confidence < 0.90` menjadi tidak akurat jika confidence = 1.1.

---

## Ringkasan Temuan

| ID | Severity | File | Masalah | Status |
|----|----------|------|---------|--------|
| BUG-001 | 🔴 KRITIS | `state_space.py` | Fear & Greed selalu hardcoded 50 | Belum diperbaiki |
| BUG-002 | 🔴 KRITIS | `agent_scorer.py` | Win rate tidak pernah dihitung | Belum diperbaiki |
| BUG-003 | 🔴 KRITIS | `risk_guard.py` | Kalkulasi exposure salah di SQL | Belum diperbaiki |
| BUG-004 | 🟡 SEDANG | `news_feed.py` | sentiment_score selalu 0.0 | Belum diperbaiki |
| BUG-005 | 🟡 SEDANG | `orchestrator.py` | current_price bisa 0 → ZeroDivision | Belum diperbaiki |
| BUG-006 | 🟡 SEDANG | `consensus.py` | proposed_size hardcoded $100 | Belum diperbaiki |
| BUG-007 | 🟡 SEDANG | `fundamental.py` | onchain_summary bisa None → crash | Belum diperbaiki |
| BUG-008 | 🟡 SEDANG | `technical.py` | Instruksi lama masih di kode Python | Belum diperbaiki |
| BUG-009 | 🟢 RINGAN | `paper_trading.py` | is_testnet hardcoded False | Belum diperbaiki |
| BUG-010 | 🟢 RINGAN | `state_space.py` | 9 feature padding sia-sia | Belum diperbaiki |
| BUG-011 | 🟢 RINGAN | `onchain_data.py` | avg_block_size key salah | Belum diperbaiki |
| BUG-012 | 🟢 RINGAN | `regime_strategy.py` | Confidence tidak di-clamp ke 1.0 | Belum diperbaiki |

---

## Rekomendasi Prioritas Perbaikan

**Fase 1 (Sekarang)**: BUG-001, BUG-002, BUG-003, BUG-007, BUG-008  
**Fase 2 (Minggu ini)**: BUG-004, BUG-005, BUG-006  
**Fase 3 (Opsional)**: BUG-009, BUG-010, BUG-011, BUG-012  
