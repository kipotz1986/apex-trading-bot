# Daftar Data Palsu / Hardcoded — APEX Bot v6

Dokumen ini mencatat semua nilai **hardcoded/dummy/tidak realistis** yang ditemukan di codebase, terpisah dari AUDIT_REPORT.md agar mudah di-track.

---

## 1. `state_space.py:51` — Fear & Greed SELALU 50

```python
features.append(market_data.get("fear_greed_index", 50) / 100.0)
# ↑ Key "fear_greed_index" tidak ada di market_data → selalu default 50
```

**Nilai palsu**: `0.5` setiap siklus, tanpa kecuali.

---

## 2. `consensus.py:114` — Proposed Trade Size SELALU $100

```python
"proposed_size": 100.0,  # Default size, will be refined by Risk Manager
```

**Nilai palsu**: `$100` flat, tidak ada hubungannya dengan equity aktual user (bisa $183k).

---

## 3. `trading_environment.py:131-134` — Agent Signals di RL Training SELALU "NEUTRAL"

```python
agent_signals = {
    "technical": "NEUTRAL",
    "fundamental": "NEUTRAL",
    "sentiment": "NEUTRAL"
}
```

**Nilai palsu**: Model RL dilatih dengan sinyal dummy. Ini berarti model RL tidak pernah belajar dari sinyal agen yang sesungguhnya selama training.

---

## 4. `paper_trading.py:64` — is_testnet Hardcoded False

```python
is_testnet=False,  # Hardcoded, tidak dinamis
```

**Nilai palsu**: Semua paper orders dicatat sebagai non-testnet, meskipun user mungkin berada di mode testnet.

---

## 5. `agent_scorer.py` — Win Rate = 0% Selamanya

`update_performance()` tidak pernah dipanggil → `successful_trades = 0` dan `score` tidak pernah berubah dari initial value `100.0`.

Dashboard menampilkan `0%` win rate untuk semua agen, tapi bukan karena agen buruk — melainkan karena evaluasi tidak pernah dijalankan.

---

## 6. `news_feed.py` — sentiment_score = 0.0 untuk Semua Berita

```python
# NormalizedNews dibuat tanpa sentiment_score
NormalizedNews(
    title=...,
    source=...,
    # sentiment_score tidak diisi → default 0.0
)
```

Semua berita dianggap "netral" (0.0), padahal ada berita sangat positif atau sangat negatif.

---

## 7. `onchain_data.py:137` — avg_block_size Selalu 0

```python
"avg_block_size": data.get("blocks_avg", 0),  # Key salah! Harusnya "avg_block_size"
```

API Blockchain.com mengembalikan key `"avg_block_size"` bukan `"blocks_avg"`.

---

## 8. `state_space.py:79-81` — 9 Feature Padding Nol Permanen

```python
while len(features) < self.feature_dim:  # feature_dim = 25
    features.append(0.0)  # 9 slot selalu 0.0
```

Model RL selalu menerima 9 input nol yang tidak bermakna, membuang kapasitas representasi.
