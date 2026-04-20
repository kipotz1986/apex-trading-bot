# Epic 10: Paper Trading & Backtesting

---

## T-10.1: Paper Trading Engine

**Labels:** `epic-10`, `paper-trading`, `simulation`, `priority-critical`
**Milestone:** Fase 3 — Execution

### Deskripsi
Membuat engine yang mensimulasikan trading dengan uang virtual tetapi menggunakan data harga real-time. Semua fungsi bot berjalan identik dengan live trading, hanya saja order tidak benar-benar dikirim ke exchange — semuanya disimulasikan di lokal.

### Mengapa WAJIB?
Owner tidak punya pengalaman trading. Bot HARUS diuji dengan uang virtual sebelum menyentuh uang sungguhan. Ini adalah "latihan tanding" sebelum "pertandingan sesungguhnya."

### Perbedaan Paper vs Live

| Aspek | Paper Trading | Live Trading |
|---|---|---|
| Data harga | Real-time (asli) | Real-time (asli) |
| Order execution | Simulasi (lokal) | Exchange API (sungguhan) |
| Balance/PnL | Virtual (dihitung lokal) | Actual (dari exchange) |
| Risiko | Nol | Uang sesungguhnya |
| Slippage/Fee | Disimulasikan (estimasi) | Actual |

### Langkah-Langkah Implementasi

#### 1. Buat `backend/app/services/paper_trading.py`

```python
"""
Paper Trading Engine.

Simulasi trading menggunakan data real-time tanpa risiko uang sungguhan.
Semua fungsi bot berjalan identik, hanya eksekusi yang disimulasikan.

Usage:
    paper = PaperTradingEngine(initial_balance=10000)
    result = await paper.execute_order("BTC/USDT", "buy", 0.01, price=50000)
"""

from datetime import datetime
from typing import Optional
from app.core.logging import get_logger

logger = get_logger(__name__)


class PaperTradingEngine:
    """Engine simulasi trading."""

    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions: dict = {}     # symbol → position info
        self.orders: list = []        # history semua order
        self.trade_history: list = [] # history trade selesai
        self.equity_history: list = []

    async def execute_order(
        self,
        symbol: str,
        side: str,       # "buy" or "sell"
        amount: float,
        price: float,    # Current market price
        order_type: str = "market",
        stop_loss: Optional[float] = None,
        take_profit: Optional[list[float]] = None,
        leverage: int = 1,
    ) -> dict:
        """Simulasi eksekusi order."""
        # Simulasi slippage (0.05% untuk market order)
        slippage = price * 0.0005 if order_type == "market" else 0
        fill_price = price + slippage if side == "buy" else price - slippage
        
        # Simulasi fee (0.1% maker/taker average)
        fee = amount * fill_price * 0.001
        
        # Kurangi balance
        cost = amount * fill_price / leverage
        self.balance -= (cost + fee)
        
        # Simpan posisi
        position = {
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "entry_price": fill_price,
            "leverage": leverage,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "fee_paid": fee,
            "opened_at": datetime.utcnow().isoformat(),
        }
        self.positions[symbol] = position
        
        order = {
            "id": f"paper_{len(self.orders)+1}",
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "price": fill_price,
            "fee": fee,
            "status": "filled",
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.orders.append(order)
        
        logger.info("paper_order_executed",
            symbol=symbol, side=side, price=fill_price, fee=fee
        )
        
        return order

    async def check_sl_tp(self, symbol: str, current_price: float) -> Optional[dict]:
        """Cek apakah SL atau TP terkena di harga saat ini."""
        if symbol not in self.positions:
            return None
        
        pos = self.positions[symbol]
        
        # Check Stop Loss
        if pos["stop_loss"]:
            if pos["side"] == "buy" and current_price <= pos["stop_loss"]:
                return await self.close_position(symbol, current_price, "stop_loss")
            if pos["side"] == "sell" and current_price >= pos["stop_loss"]:
                return await self.close_position(symbol, current_price, "stop_loss")
        
        # Check Take Profit (first level)
        if pos["take_profit"] and len(pos["take_profit"]) > 0:
            tp1 = pos["take_profit"][0]
            if pos["side"] == "buy" and current_price >= tp1:
                return await self.close_position(symbol, current_price, "take_profit")
            if pos["side"] == "sell" and current_price <= tp1:
                return await self.close_position(symbol, current_price, "take_profit")
        
        return None

    async def close_position(self, symbol, price, reason="manual") -> dict:
        """Tutup posisi dan hitung PnL."""
        pos = self.positions.pop(symbol)
        
        if pos["side"] == "buy":
            pnl = (price - pos["entry_price"]) * pos["amount"] * pos["leverage"]
        else:
            pnl = (pos["entry_price"] - price) * pos["amount"] * pos["leverage"]
        
        pnl -= pos["fee_paid"]  # Kurangi fee entry
        close_fee = pos["amount"] * price * 0.001  # Fee exit
        pnl -= close_fee
        
        self.balance += (pos["amount"] * pos["entry_price"] / pos["leverage"]) + pnl
        
        trade = {
            "symbol": symbol,
            "side": pos["side"],
            "entry_price": pos["entry_price"],
            "exit_price": price,
            "amount": pos["amount"],
            "pnl": round(pnl, 2),
            "pnl_pct": round((pnl / (pos["amount"] * pos["entry_price"])) * 100, 2),
            "close_reason": reason,
            "opened_at": pos["opened_at"],
            "closed_at": datetime.utcnow().isoformat(),
        }
        self.trade_history.append(trade)
        
        logger.info("paper_position_closed",
            symbol=symbol, pnl=pnl, reason=reason
        )
        
        return trade

    def get_stats(self) -> dict:
        """Dapatkan statistik performa paper trading."""
        if not self.trade_history:
            return {"total_trades": 0}
        
        wins = [t for t in self.trade_history if t["pnl"] > 0]
        losses = [t for t in self.trade_history if t["pnl"] <= 0]
        
        return {
            "total_trades": len(self.trade_history),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(len(wins) / len(self.trade_history) * 100, 1),
            "total_pnl": round(sum(t["pnl"] for t in self.trade_history), 2),
            "avg_win": round(sum(t["pnl"] for t in wins) / len(wins), 2) if wins else 0,
            "avg_loss": round(sum(t["pnl"] for t in losses) / len(losses), 2) if losses else 0,
            "current_balance": round(self.balance, 2),
            "return_pct": round((self.balance - self.initial_balance) / self.initial_balance * 100, 2),
        }
```

### Definition of Done
- [ ] Paper trading berjalan dengan data harga real-time
- [ ] Slippage dan fee disimulasikan secara realistis
- [ ] SL dan TP trigger berfungsi
- [ ] Statistik performa akurat
- [ ] Semua data disimpan di database (sama seperti live)
- [ ] Dashboard bisa menampilkan paper trading data

### File yang Dibuat
- `[NEW]` `backend/app/services/paper_trading.py`

---

## T-10.2: Backtesting Framework

**Labels:** `epic-10`, `backtesting`, `simulation`, `priority-critical`
**Milestone:** Fase 3 — Execution

### Deskripsi
Framework untuk menjalankan strategi bot terhadap data historis. Ini menjawab pertanyaan: "Jika bot ini sudah ada 6 bulan lalu, berapa profit/rugi-nya?"

### Perbedaan Paper Trading vs Backtesting

| | Paper Trading | Backtesting |
|---|---|---|
| Waktu | Real-time (masa depan) | Historis (masa lalu) |
| Kecepatan | 1:1 (real) | Ribuan kali lebih cepat |
| Data | Live market | Data historis dari DB |
| Tujuan | Validasi sebelum live | Evaluasi & optimasi strategi |

### Langkah-Langkah
1. Buat `backend/app/services/backtesting.py`
2. Input: tanggal mulai, tanggal selesai, pair, initial balance
3. Load candle data dari TimescaleDB
4. Simulasikan: jalankan agent analysis di setiap candlestick, buat keputusan, simulasikan order
5. Kumpulkan metrik

### Definition of Done
- [ ] Bisa backtest minimal 6 bulan data historis
- [ ] Semua agent berjalan di setiap step
- [ ] Metrik terhitung: Win Rate, Max Drawdown, Sharpe Ratio, PnL
- [ ] Berjalan jauh lebih cepat dari real-time

### File yang Dibuat
- `[NEW]` `backend/app/services/backtesting.py`

---

## T-10.3: Metrik Backtesting

**Labels:** `epic-10`, `backtesting`, `analytics`, `priority-high`
**Milestone:** Fase 3 — Execution
**Depends On:** T-10.2

### Deskripsi
Implementasi kalkulasi metrik performa professional.

### Metrik yang Dihitung

| Metrik | Formula/Penjelasan | Target |
|---|---|---|
| **Win Rate** | Wins / Total Trades × 100 | ≥ 55% |
| **Profit Factor** | Gross Profit / Gross Loss | > 1.5 |
| **Sharpe Ratio** | (Avg Return - Risk Free) / Std Dev | > 1.0 |
| **Max Drawdown** | Max peak-to-trough decline | < 15% |
| **Avg Win / Avg Loss** | Avg winning trade / Avg losing trade | > 1.5 |
| **Expectancy** | (Win% × Avg Win) - (Loss% × Avg Loss) | > 0 |
| **Total Return** | (Final Balance - Initial) / Initial × 100 | Positif |
| **Trade Frequency** | Trades per day | 2-10 |

### Definition of Done
- [ ] Semua 8 metrik diimplementasi dengan benar
- [ ] Output sebagai structured report
- [ ] Bisa dibandingkan antar backtest run

---

## T-10.4: Dashboard Panel Backtesting Results

**Labels:** `epic-10`, `dashboard`, `visualization`, `priority-medium`
**Milestone:** Fase 3 — Execution
**Depends On:** T-10.2, T-10.3

### Deskripsi
Endpoint API + visualisasi equity curve (grafik pertumbuhan balance dari waktu ke waktu) dari hasil backtesting.

### Langkah-Langkah
1. Endpoint REST: `POST /api/backtest/run` (trigger backtest)
2. Endpoint REST: `GET /api/backtest/results/{id}` (ambil hasil)
3. Data untuk chart: array `[{date, balance, equity, drawdown}]`
4. Dashboard menampilkan equity curve chart + tabel metrik

### Definition of Done
- [ ] Backtest bisa di-trigger via API
- [ ] Hasil backtest tersimpan dan bisa di-retrieve
- [ ] Data siap untuk visualisasi chart

---

## T-10.5: Mode Switch: Paper → Live

**Labels:** `epic-10`, `execution`, `safety`, `priority-critical`
**Milestone:** Fase 3 — Execution

### Deskripsi
Implementasi mekanisme switch dari Paper Trading ke Live Trading. Harus ada **double confirmation** untuk mencegah switch tidak disengaja.

### Safety Checks Sebelum Switch ke Live
1. Paper trading sudah berjalan minimum 14 hari
2. Win rate paper ≥ 55%
3. Max drawdown paper < 15%
4. User mengkonfirmasi via dashboard (toggle + popup confirmation)
5. Log switch event di audit trail

### Definition of Done
- [ ] Switch membutuhkan double confirmation
- [ ] Safety checks harus pass sebelum Live diizinkan
- [ ] Audit trail tercatat

---

## T-10.6: Minimum Paper Trading Period Enforcement

**Labels:** `epic-10`, `safety`, `priority-critical`
**Milestone:** Fase 3 — Execution

### Deskripsi
Memaksa bot menjalankan paper trading minimal **14 hari** sebelum mode Live bisa diaktifkan. Ini hardcoded dan TIDAK bisa di-bypass.

### Langkah-Langkah
1. Track start date paper trading di database
2. Di switch ke Live (T-10.5), check: `(today - start_date) >= 14 days`
3. Jika belum 14 hari: tolak switch, tampilkan: "Paper trading harus berjalan minimal 14 hari. Sisa: X hari."

### Definition of Done
- [ ] 14 hari minimum enforced
- [ ] Tidak bisa di-bypass
- [ ] Pesan error jelas
