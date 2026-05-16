# Fix Checklist — Audit v6

Checklist ini mengikuti prioritas dari AUDIT_REPORT.md.

---

## FASE 1 — Kritis & Blockers

- [ ] **BUG-001** `state_space.py:51` — Ganti `market_data.get("fear_greed_index", 50)` dengan parsing dari `composite_sentiment.score`
- [ ] **BUG-002** `agent_scorer.py` — Tambahkan pemanggilan `update_performance()` di `position_monitor.py` saat posisi ditutup
- [ ] **BUG-003** `risk_guard.py:80-84` — Perbaiki kalkulasi exposure: ambil semua order FILLED lalu sum secara Python, bukan di query level
- [ ] **BUG-007** `fundamental.py:52` — Tambahkan null check: `if onchain_summary:` sebelum `.model_dump()`
- [ ] **BUG-008** `technical.py:165` — Hapus `"If alignment is true, boost confidence."` dari instruksi hardcoded

## FASE 2 — Perhitungan & Data

- [ ] **BUG-004** `news_feed.py` — Implementasi simple sentiment_score dari judul berita (keyword matching atau LLM mini)
- [ ] **BUG-005** `orchestrator.py:221` — Tambahkan validasi `current_price > 0` + fallback ke ticker real-time
- [ ] **BUG-006** `consensus.py:114` — Ganti `proposed_size: 100.0` dengan kalkulasi dinamis dari equity portfolio

## FASE 3 — Cleanup & Optimasi

- [ ] **BUG-009** `paper_trading.py:64` — Baca `is_testnet` dari RiskState/Settings
- [ ] **BUG-010** `state_space.py` — Tambah 9 feature bermakna (OI, hash rate, volume ratio, dll) untuk menghilangkan padding
- [ ] **BUG-011** `onchain_data.py:137` — Perbaiki key `"blocks_avg"` → `"avg_block_size"`
- [ ] **BUG-012** `regime_strategy.py:60` — Clamp confidence ke max 1.0 sebelum komparasi
