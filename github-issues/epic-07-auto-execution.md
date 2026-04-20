# Epic 7: Auto-Execution & Order Management

---

## T-7.1: Integrasi CCXT untuk Execution (Create/Cancel/Modify Order)

**Labels:** `epic-7`, `execution`, `integration`, `priority-critical`
**Milestone:** Fase 3 — Execution
**Depends On:** T-3.1

### Deskripsi
Membuat service yang megeksekusi order jual/beli di exchange menggunakan CCXT. Ini adalah momen kritis — di sinilah uang turun. Oleh karena itu, setiap eksekusi harus melalui validasi ketat dan logging detail.

### PENTING: Safety First!
- Awalnya **SELALU gunakan testnet/sandbox** (`EXCHANGE_TESTNET=true`)
- Setiap order harus dicatat di database SEBELUM dikirim ke exchange
- Retry logic harus bijak — JANGAN retry market order (bisa double entry!)

### Langkah-Langkah Implementasi

#### 1. Buat `backend/app/services/execution.py`

```python
"""
Order Execution Engine.

Bertanggung jawab untuk mengirim order ke exchange dan
mengelola lifecycle order (create, monitor, cancel).

SAFETY RULES:
- Setiap order dicatat di DB sebelum dieksekusi
- Market order TIDAK pernah di-retry (risiko double entry)
- Limit order bisa di-retry (idempotent)
- Pre-trade validation WAJIB lulus sebelum eksekusi

Usage:
    executor = ExecutionEngine(exchange_service)
    result = await executor.open_position(
        symbol="BTC/USDT",
        side="buy",
        amount=0.01,
        order_type="limit",
        price=50000,
        stop_loss=49000,
        take_profit=[51000, 52000, 53000],
    )
"""

from typing import Optional
from app.services.exchange import ExchangeService
from app.core.logging import get_logger

logger = get_logger(__name__)


class ExecutionEngine:
    """Engine untuk eksekusi order di exchange."""

    def __init__(self, exchange: ExchangeService):
        self.exchange = exchange

    async def open_position(
        self,
        symbol: str,
        side: str,           # "buy" (long) atau "sell" (short)
        amount: float,       # Jumlah asset
        order_type: str,     # "market" atau "limit"
        price: Optional[float] = None,  # Wajib untuk limit order
        stop_loss: Optional[float] = None,
        take_profit: Optional[list[float]] = None,
        leverage: int = 1,
    ) -> dict:
        """
        Buka posisi baru di exchange.
        
        Returns:
            dict dengan order ID, status, filled price, dll.
        """
        # 1. Log intention ke database
        # 2. Set leverage
        # 3. Create main order
        # 4. Set stop loss
        # 5. Set take profit (multi-level)
        # 6. Update status di database
        # 7. Return result

        logger.info("opening_position",
            symbol=symbol, side=side, amount=amount,
            order_type=order_type, leverage=leverage
        )

        try:
            # Set leverage
            await self.exchange.exchange.set_leverage(leverage, symbol)

            # Create order
            if order_type == "market":
                order = await self.exchange.exchange.create_market_order(
                    symbol, side, amount
                )
            elif order_type == "limit":
                if price is None:
                    raise ValueError("Price wajib untuk limit order")
                order = await self.exchange.exchange.create_limit_order(
                    symbol, side, amount, price
                )

            logger.info("order_created",
                order_id=order["id"],
                symbol=symbol,
                filled_price=order.get("average"),
            )

            # Set SL dan TP setelah order terisi
            if order.get("status") == "closed" or order_type == "market":
                if stop_loss:
                    await self._set_stop_loss(symbol, side, amount, stop_loss)
                if take_profit:
                    await self._set_take_profits(symbol, side, amount, take_profit)

            return order

        except Exception as e:
            logger.error("order_execution_error",
                symbol=symbol, side=side, error=str(e)
            )
            raise

    async def close_position(
        self,
        symbol: str,
        side: str,       # side dari posisi yang ditutup
        amount: float,   # jumlah yang ditutup (bisa partial)
    ) -> dict:
        """Tutup posisi (sebagian atau seluruhnya)."""
        # Untuk menutup, kita buka order ke arah berlawanan
        close_side = "sell" if side == "buy" else "buy"
        return await self.exchange.exchange.create_market_order(
            symbol, close_side, amount,
            params={"reduceOnly": True}  # Pastikan hanya close, bukan buka baru
        )

    async def cancel_order(self, order_id: str, symbol: str) -> dict:
        """Cancel pending order."""
        return await self.exchange.exchange.cancel_order(order_id, symbol)

    async def _set_stop_loss(self, symbol, side, amount, price):
        """Set stop loss order."""
        sl_side = "sell" if side == "buy" else "buy"
        await self.exchange.exchange.create_order(
            symbol, "stop", sl_side, amount, price,
            params={"reduceOnly": True, "triggerPrice": price}
        )
        logger.info("stop_loss_set", symbol=symbol, price=price)

    async def _set_take_profits(self, symbol, side, amount, prices):
        """Set multi-level take profit orders."""
        tp_side = "sell" if side == "buy" else "buy"
        # Bagi amount ke TP levels (contoh: 3 level = 33% each)
        per_level = amount / len(prices)
        for i, price in enumerate(prices):
            await self.exchange.exchange.create_order(
                symbol, "take_profit", tp_side, per_level, price,
                params={"reduceOnly": True, "triggerPrice": price}
            )
            logger.info("take_profit_set",
                symbol=symbol, level=i+1, price=price, amount=per_level
            )
```

### Definition of Done
- [ ] Open position (market + limit order) berfungsi
- [ ] Close position (full + partial) berfungsi
- [ ] Cancel order berfungsi
- [ ] Stop Loss otomatis ter-set setelah entry
- [ ] Take Profit multi-level berfungsi
- [ ] Leverage bisa di-set
- [ ] Semua aksi terlog di database
- [ ] Tested di testnet/sandbox

### File yang Dibuat
- `[NEW]` `backend/app/services/execution.py`
- `[NEW]` `backend/app/models/order.py`

---

## T-7.2: Implementasi Order Types (Market, Limit, Stop-Limit)

**Labels:** `epic-7`, `execution`, `priority-high`
**Milestone:** Fase 3 — Execution
**Depends On:** T-7.1

### Deskripsi
Memastikan semua tipe order yang dibutuhkan bisa dieksekusi dengan benar.

### Tipe Order

| Tipe | Kapan Digunakan | Kelebihan | Kekurangan |
|---|---|---|---|
| **Market** | Perlu masuk/keluar sekarang juga | Pasti tereksekusi | Mungkin ada slippage |
| **Limit** | Mau masuk di harga tertentu | Harga dijamin, fee lebih murah | Mungkin tidak tereksekusi |
| **Stop-Limit** | Proteksi (SL/TP) | Kontrol penuh | Mungkin skip di market gap |

### Langkah-Langkah
1. Extend ExecutionEngine dengan method untuk setiap tipe order
2. Validasi parameter per tipe (limit harus ada price, dll.)
3. Test setiap tipe di sandbox

### Definition of Done
- [ ] Market order berfungsi
- [ ] Limit order berfungsi
- [ ] Stop-Limit order berfungsi
- [ ] Validasi parameter sebelum eksekusi

---

## T-7.3: Stop Loss & Take Profit Multi-Level

**Labels:** `epic-7`, `execution`, `risk-management`, `priority-critical`
**Milestone:** Fase 3 — Execution
**Depends On:** T-7.1

### Deskripsi
Implementasi SL dan TP yang canggih. TP multi-level berarti mengambil sebagian profit di beberapa target, bukan sekaligus.

### Contoh Multi-Level TP
Beli BTC di $60,000 dengan total 0.1 BTC:
- **TP1:** $61,000 → Jual 0.033 BTC (33%) — mengamankan sebagian profit
- **TP2:** $62,500 → Jual 0.033 BTC (33%) — profit lebih besar
- **TP3:** $65,000 → Jual 0.034 BTC (34%) — maximum profit
- **SL:** $58,500 → Jual semua sisa — membatasi kerugian

### Langkah-Langkah
1. Implementasi `_set_take_profits()` dengan partial close
2. Implementasi dynamic SL adjustment (geser SL ke entry price setelah TP1 kena)
3. Logging setiap TP/SL yang terkena
4. Update database: order status, actual profit/loss

### Definition of Done
- [ ] Multi-level TP berfungsi (TP1, TP2, TP3)
- [ ] Partial close pada setiap level
- [ ] SL bisa digeser setelah TP1 terkena
- [ ] Database ter-update setiap event

---

## T-7.4: Implementasi Trailing Stop

**Labels:** `epic-7`, `execution`, `priority-high`
**Milestone:** Fase 3 — Execution

### Deskripsi
Trailing stop adalah stop loss yang otomatis mengikuti harga saat bergerak menguntungkan, tapi tetap diam saat harga bergerak berlawanan. Ini mengunci profit maksimal.

### Contoh
Beli BTC di $60,000, trailing stop distance = $1,000:
- Harga naik ke $61,000 → SL naik ke $60,000 (break-even)
- Harga naik ke $63,000 → SL naik ke $62,000
- Harga turun ke $62,000 → SL terkena → Profit $2,000!

Tanpa trailing: mungkin profit hanya $1,000 (di TP1)
Dengan trailing: profit bisa $2,000+ karena mengikuti pergerakan

### Langkah-Langkah
1. Implementasi via exchange native trailing stop (jika exchange mendukung)
2. ATAU implementasi manual: monitor harga, update SL setiap kali harga naik
3. Distance bisa fixed (USD) atau percentage
4. Minimum activation: trailing baru aktif setelah profit > X%

### Definition of Done
- [ ] Trailing stop berfungsi (exchange native atau manual)
- [ ] SL otomatis naik mengikuti harga
- [ ] SL tidak pernah turun
- [ ] Activation threshold configurable

---

## T-7.5: Pre-Trade Validation Checklist

**Labels:** `epic-7`, `execution`, `risk-management`, `priority-critical`
**Milestone:** Fase 3 — Execution
**Depends On:** T-7.1, Epic 8

### Deskripsi
Sebelum SETIAP order dikirim ke exchange, checklist validasi harus lulus 100%. Ini adalah gerbang terakhir sebelum uang benar-benar berisiko.

### Checklist

```python
async def pre_trade_validation(self, trade_decision) -> tuple[bool, str]:
    """
    Return (True, "") jika valid, (False, "alasan") jika ditolak.
    SEMUA check harus pass. Satu saja gagal = trade ditolak.
    """
    checks = [
        self._check_risk_approval(trade_decision),     # Risk Manager approved?
        self._check_consensus_threshold(trade_decision),# Consensus ≥ threshold?
        self._check_daily_loss_limit(),                 # Belum kena daily limit?
        self._check_max_exposure(),                     # Exposure tidak berlebihan?
        self._check_sufficient_balance(trade_decision), # Saldo cukup + fee?
        self._check_spread_slippage(trade_decision),    # Spread wajar?
        self._check_bot_enabled(),                      # Bot nyala?
        self._check_cooldown_period(),                  # Sudah lewat cooldown?
    ]
    
    for check_name, passed, reason in checks:
        if not passed:
            logger.warning("pre_trade_rejected",
                check=check_name, reason=reason
            )
            return False, f"[{check_name}] {reason}"
    
    return True, ""
```

### Definition of Done
- [ ] Semua 8 check diimplementasi
- [ ] Satu check gagal = trade ditolak (tanpa exception)
- [ ] Alasan penolakan tercatat di log
- [ ] Cannot be bypassed — hardcoded, bukan AI-controlled

---

## T-7.6: Position Monitor — Tracking Posisi Aktif

**Labels:** `epic-7`, `execution`, `monitoring`, `priority-high`
**Milestone:** Fase 3 — Execution

### Deskripsi
Service yang terus memantau semua posisi terbuka secara real-time. Ini memungkinkan dynamic SL/TP adjustment dan monitoring floating PnL.

### Langkah-Langkah
1. Buat `backend/app/services/position_monitor.py`
2. Poll posisi terbuka dari exchange setiap 10 detik
3. Hitung floating PnL real-time
4. Deteksi SL/TP hit events
5. Broadcast data ke dashboard via WebSocket
6. Trigger alert jika posisi mendekati liquidation

### Definition of Done
- [ ] Semua open positions ter-track real-time
- [ ] Floating PnL dihitung dengan benar (termasuk fee)
- [ ] SL/TP hit terdeteksi dan ter-log
- [ ] Data streaming ke dashboard

### File yang Dibuat
- `[NEW]` `backend/app/services/position_monitor.py`

---

## T-7.7: Anti-Liquidation Guard

**Labels:** `epic-7`, `execution`, `risk-management`, `priority-critical`
**Milestone:** Fase 3 — Execution

### Deskripsi
Proteksi otomatis untuk mencegah posisi terkena liquidation (ditutup paksa oleh exchange karena margin habis). Ini adalah skenario TERBURUK yang harus dihindari.

### Mekanisme
1. Monitor margin ratio setiap posisi
2. Jika margin ratio < 30% → kurangi ukuran posisi 50%
3. Jika margin ratio < 20% → tutup posisi
4. Alert darurat dikirim via Telegram

### Definition of Done
- [ ] Margin ratio dipantau real-time
- [ ] Auto-reduce saat mendekati bahaya
- [ ] Auto-close sebagai last resort
- [ ] Alert dikirim

---

## T-7.8: Slippage Protection & Fee-Aware Profit Calculation

**Labels:** `epic-7`, `execution`, `priority-medium`
**Milestone:** Fase 3 — Execution

### Deskripsi
Memastikan bot memperhitungkan biaya trading (fee maker/taker, funding fee) dan slippage saat menghitung profitabilitas trade.

### Langkah-Langkah
1. Ambil fee rate dari exchange API
2. Kalkulasi: `net_profit = gross_profit - entry_fee - exit_fee - funding_fee`
3. Slippage guard: jika spread > 0.1%, gunakan limit order daripada market
4. Minimum profit threshold: jangan trade jika expected profit < total fee

### Definition of Done
- [ ] Fee rate otomatis diambil dari exchange
- [ ] Net profit sudah termasuk semua fee
- [ ] Slippage guard aktif
- [ ] Minimum profit threshold diterapkan

---

## T-7.9: Cooldown Period Antar Trade

**Labels:** `epic-7`, `execution`, `risk-management`, `priority-medium`
**Milestone:** Fase 3 — Execution

### Deskripsi
Setelah trade ditutup, bot wajib menunggu minimal 5 menit (configurable) sebelum membuka trade baru. Ini mencegah "revenge trading" — membuka posisi impulsif setelah kerugian.

### Langkah-Langkah
1. Simpan timestamp trade terakhir di Redis
2. Di pre-trade validation (T-7.5), check apakah cooldown sudah lewat
3. Cooldown configurable: default 5 menit, bisa diubah
4. Cooldown lebih panjang setelah loss (10 menit)

### Definition of Done
- [ ] Cooldown enforced di pre-trade validation
- [ ] Cooldown lebih panjang setelah loss
- [ ] Configurable via settings

---

## T-7.10: Error Handling & Retry Logic untuk API Exchange

**Labels:** `epic-7`, `execution`, `reliability`, `priority-high`
**Milestone:** Fase 3 — Execution

### Deskripsi
Handle semua kemungkinan error saat berkomunikasi dengan exchange API.

### Error Scenarios

| Error | Handling |
|---|---|
| Rate Limited (429) | Exponential backoff, retry setelah wait |
| Timeout | Retry max 3x, increment timeout |
| Partial Fill | Track partially filled orders, update database |
| Insufficient Balance | Reject, log, notify |
| Network Error | Retry max 3x, switch to backup connection |
| Exchange Maintenance | Pause all trading, notify, auto-resume |

### ⚠️ ATURAN PENTING
- **Market order TIDAK boleh di-retry** — bisa menyebabkan double entry!
- **Limit order boleh di-retry** — karena idempotent (order duplikat = hanya 1 yang terisi)
- Setelah retry gagal → catat di database, kirim alert, jangan crash

### Definition of Done
- [ ] Semua error scenario dari tabel di atas ter-handle
- [ ] Market order TIDAK di-retry
- [ ] Limit order di-retry max 3x
- [ ] Alert dikirim untuk error yang tidak bisa di-resolve
