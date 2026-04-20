# Epic 8: Risk Management & Circuit Breaker

---

## T-8.1: Daily Loss Limit

**Labels:** `epic-8`, `risk-management`, `circuit-breaker`, `priority-critical`
**Milestone:** Fase 3 — Execution

### Deskripsi
Implementasi batas kerugian harian. Jika total kerugian dalam 1 hari melebihi 3% dari total modal, bot berhenti trading selama 24 jam secara otomatis.

### Mengapa 3%?
- Profesional hedge fund biasanya memakai 1–2% daily loss limit
- 3% sudah cukup agresif untuk bot trading, tapi masih aman
- Dengan 3%/hari, butuh 5 hari berturut-turut untuk rugi 15% — sebelum itu weekly limit sudah menghentikan

### Langkah-Langkah
1. Buat `backend/app/services/risk/circuit_breaker.py`
2. Hitung total realized PnL hari ini dari database
3. Bandingkan dengan 3% dari total modal
4. Jika terlewati: set flag `bot_paused = true`, schedule resume 24 jam kemudian
5. Kirim alert Telegram: "⚠️ Daily loss limit reached: -3.2%. Bot paused for 24 hours."
6. Log di database: timestamp, loss amount, modal saat itu

### Implementasi
```python
class CircuitBreaker:
    async def check_daily_loss(self) -> tuple[bool, str]:
        """Return (is_triggered, reason)"""
        total_capital = await self._get_total_capital()
        daily_pnl = await self._get_daily_pnl()
        daily_loss_pct = (daily_pnl / total_capital) * 100
        
        if daily_loss_pct <= -3.0:  ## Rugi 3% atau lebih
            return True, f"Daily loss {daily_loss_pct:.1f}% exceeds -3% limit"
        return False, ""
```

### Definition of Done
- [ ] Daily PnL dihitung dengan benar (semua closed trades hari ini)
- [ ] Bot berhenti saat limit tercapai
- [ ] Bot otomatis resume setelah 24 jam
- [ ] Alert Telegram terkirim
- [ ] Event terlog di database

### File yang Dibuat
- `[NEW]` `backend/app/services/risk/circuit_breaker.py`
- `[NEW]` `backend/app/services/risk/__init__.py`

---

## T-8.2: Weekly Loss Limit

**Labels:** `epic-8`, `risk-management`, `circuit-breaker`, `priority-critical`
**Milestone:** Fase 3 — Execution
**Depends On:** T-8.1

### Deskripsi
Batas kerugian mingguan (7%). Jika tercapai, bot berhenti **sampai manual review**. Tidak auto-resume — memaksa owner untuk mengevaluasi situasi.

### Mengapa Manual Review?
7% dalam 1 minggu menandakan ada sesuatu yang sangat salah (market crash, bug strategi, dll). Bot perlu dievaluasi sebelum dilanjutkan.

### Langkah-Langkah
1. Hitung PnL 7 hari terakhir
2. Jika rugi ≥ 7%: pause bot, set status "REQUIRES_REVIEW"
3. Alert Telegram: "🔴 Weekly loss limit reached: -7.5%. Bot stopped. Manual review required. Resume via dashboard."
4. Bot hanya bisa di-resume via toggle di dashboard (Epic 12)

### Definition of Done
- [ ] Weekly PnL dihitung dengan benar (rolling 7 hari)
- [ ] Bot berhenti dan TIDAK auto-resume
- [ ] Alert Telegram terkirim
- [ ] Hanya bisa di-resume manual via dashboard

---

## T-8.3: Max Drawdown Guard

**Labels:** `epic-8`, `risk-management`, `circuit-breaker`, `priority-critical`
**Milestone:** Fase 3 — Execution

### Deskripsi
Proteksi paling agresif. Jika equity (total nilai portfolio) turun 15% dari titik tertinggi (peak), bot **tutup semua posisi** dan berhenti total.

### Apa itu Drawdown?
Drawdown = penurunan dari puncak.
- Modal awal: Rp100 juta
- Puncak: Rp120 juta
- Equity saat ini: Rp102 juta
- Drawdown = (120 - 102) / 120 = 15% ← **TRIGGER!**

### Langkah-Langkah
1. Track equity peak (nilai tertinggi yang pernah dicapai)
2. Hitung current drawdown: `(peak - current) / peak * 100`
3. Warning di 10% drawdown (alert)
4. STOP + CLOSE ALL di 15% drawdown (emergency)
5. Kirim alert darurat Telegram
6. Status: "EMERGENCY_STOPPED"

### Definition of Done
- [ ] Equity peak ter-track dan update otomatis
- [ ] Warning alert di 10% drawdown
- [ ] Emergency stop + close all positions di 15%
- [ ] Bot tidak bisa trading sampai manual reset

---

## T-8.4: Consecutive Loss Guard

**Labels:** `epic-8`, `risk-management`, `priority-high`
**Milestone:** Fase 3 — Execution

### Deskripsi
Jika 5 trade berturut-turut rugi, bot pause 6 jam dan ukuran posisi dikurangi 50% untuk 5 trade berikutnya.

### Mengapa?
5 loss berturut-turut biasanya berarti:
- Market condition tidak cocok dengan strategi saat ini
- Ada anomali yang tidak terdeteksi
- Perlu "cooling off" untuk evaluasi

### Langkah-Langkah
1. Track consecutive losses counter di Redis
2. Reset counter setiap kali ada winning trade
3. Di loss ke-5: pause 6 jam, set `position_size_multiplier = 0.5`
4. Setelah 5 trade berikutnya, jika win rate kembali normal → reset multiplier ke 1.0

### Definition of Done
- [ ] Consecutive loss counter berfungsi
- [ ] Pause 6 jam setelah 5 consecutive losses
- [ ] Position size dikurangi 50%
- [ ] Reset otomatis setelah performa membaik

---

## T-8.5: API Error Spike Detection

**Labels:** `epic-8`, `reliability`, `priority-high`
**Milestone:** Fase 3 — Execution

### Deskripsi
Jika terjadi 5+ error berturut-turut saat berkomunikasi dengan exchange API, bot pause trading dan kirim alert. Ini bisa menandakan exchange maintenance, API issue, atau masalah jaringan.

### Langkah-Langkah
1. Counter error berturut-turut di Redis (reset setiap sukses)
2. Di error ke-5: pause trading
3. Retry connection setiap 5 menit
4. Auto-resume saat koneksi kembali stabil (3 sukses berturut)
5. Alert Telegram saat pause dan saat resume

### Definition of Done
- [ ] Error counter berfungsi
- [ ] Pause otomatis setelah 5 error
- [ ] Auto-resume saat stabil
- [ ] Alert terkirim

---

## T-8.6: Position Sizing Rules

**Labels:** `epic-8`, `risk-management`, `priority-critical`
**Milestone:** Fase 3 — Execution

### Deskripsi
Implementasi aturan ukuran posisi yang ketat untuk mencegah over-exposure.

### Rules
1. **Max 5% per posisi:** Tidak boleh mempertaruhkan lebih dari 5% total modal di satu trade
2. **Max 20% total exposure:** Jumlah semua posisi terbuka tidak boleh melebihi 20% modal
3. **Kalkulasi berdasarkan balance SAAT INI**, bukan balance awal

### Implementasi
```python
async def calculate_position_size(
    self,
    trade_decision: TradeDecision,
    balance: float,
) -> float:
    """
    Hitung ukuran posisi yang aman.
    
    Perhitungan:
    1. Max per trade = balance × 0.05 (5%)
    2. Kurangi current exposure dari max total (20%)
    3. Ambil minimum dari keduanya
    4. Apply regime multiplier (sideways/volatile = lebih kecil)
    """
    max_per_trade = balance * 0.05
    max_total = balance * 0.20
    current_exposure = await self._get_total_open_exposure()
    available_exposure = max_total - current_exposure
    
    size = min(max_per_trade, available_exposure, trade_decision.position_size_usd)
    
    # Apply regime multiplier
    size *= self._get_regime_multiplier()
    
    return max(size, 0)  # Tidak boleh negatif
```

### Definition of Done
- [ ] 5% per-trade limit diterapkan
- [ ] 20% total exposure limit diterapkan
- [ ] Kalkulasi real-time berdasarkan balance aktual
- [ ] Regime multiplier diterapkan

---

## T-8.7: Correlation Guard

**Labels:** `epic-8`, `risk-management`, `priority-medium`
**Milestone:** Fase 3 — Execution

### Deskripsi
Mencegah membuka posisi yang berkorelasi tinggi secara bersamaan. BTC dan ETH sering bergerak bersama — jika sudah LONG BTC, membuka LONG ETH berarti menggandakan risiko yang sama.

### Langkah-Langkah
1. Hitung korelasi harga antar semua pair aktif (rolling 30 hari)
2. Jika korelasi > 0.8 dan sudah ada posisi di pair A, tolak posisi di pair B ke arah yang sama
3. Korelasi bisa di-cache (update harian)

### Definition of Done
- [ ] Korelasi antar pair dihitung dengan benar
- [ ] Trade di pair berkorelasi tinggi ditolak
- [ ] Cache korelasi update harian

---

## T-8.8: Dashboard Display Risk Metrics

**Labels:** `epic-8`, `dashboard`, `priority-medium`
**Milestone:** Fase 3 — Execution

### Deskripsi
Menyediakan endpoint API yang menyajikan semua risk metrics aktif untuk ditampilkan di dashboard (Epic 12).

### Data yang Disajikan
- Current drawdown %
- Daily PnL %
- Weekly PnL %
- Consecutive loss count
- Total exposure %
- Circuit breaker status (active/inactive)
- Position size multiplier

### Definition of Done
- [ ] REST endpoint `/api/risk/metrics` tersedia
- [ ] Semua metrik dihitung real-time
- [ ] Data akurat

---

## T-8.9: Alert System untuk Circuit Breaker Events

**Labels:** `epic-8`, `notification`, `priority-high`
**Milestone:** Fase 3 — Execution
**Depends On:** T-8.1 s/d T-8.5, Epic 11

### Deskripsi
Memastikan setiap trigger circuit breaker mengirim alert Telegram instan. Alert harus jelas dan menyertakan informasi yang dibutuhkan untuk evaluasi.

### Format Alert
```
🔴 CIRCUIT BREAKER TRIGGERED

Type: Daily Loss Limit
Trigger: Daily PnL = -3.2% (limit: -3.0%)
Action: Trading paused for 24 hours
Resume: 2026-04-21 07:00 WIB (auto)

📊 Current Status:
• Total Balance: $9,680
• Open Positions: 2
• Today's Trades: 8 (3 Win / 5 Loss)
```

### Definition of Done
- [ ] Alert terkirim untuk setiap tipe circuit breaker
- [ ] Format jelas dan informatif
- [ ] Terkirim dalam < 30 detik setelah trigger
