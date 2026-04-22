"""
Backtesting Framework.

Menjalankan simulasi strategi terhadap data historis (Time-travel).
Menghitung metrik performa: Sharpe Ratio, Win Rate, Drawdown.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from app.services.paper_trading import PaperTradingEngine
from app.core.logging import get_logger

logger = get_logger(__name__)

class BacktestEngine:
    """Mesin untuk pengujian historis."""

    def __init__(self, db, orchestrator):
        self.db = db
        self.orchestrator = orchestrator
        self.simulator = PaperTradingEngine(db)

    async def run(
        self, 
        symbol: str, 
        historical_candles: List[Dict[str, Any]], 
        initial_balance: float = 10000
    ) -> Dict[str, Any]:
        """
        Input: List of candles {timestamp, open, high, low, close, volume}
        """
        logger.info("backtest_started", symbol=symbol, candles=len(historical_candles))
        
        balance = initial_balance
        equity_history = []
        trades = []
        position = None # None, 'LONG', or 'SHORT'
        entry_price = 0
        entry_time = None
        
        # 1. Loop through time bits
        for i in range(50, len(historical_candles)): # Start after 50 candles
            current_candle = historical_candles[i]
            window = historical_candles[i-50:i+1]
            
            # Simple rule-based logic for backtest (to avoid 1000s of LLM calls)
            df = pd.DataFrame(window)
            import pandas_ta as ta
            rsi = ta.rsi(df["close"], length=14).iloc[-1]
            ema_short = ta.ema(df["close"], length=9).iloc[-1]
            ema_long = ta.ema(df["close"], length=21).iloc[-1]
            
            action = "HOLD"
            if position is None:
                if rsi < 35 and ema_short > ema_long:
                    action = "BUY"
                elif rsi > 65 and ema_short < ema_long:
                    action = "SELL"
            else:
                # Exit logic
                if position == "LONG" and (rsi > 70 or ema_short < ema_long):
                    action = "CLOSE"
                elif position == "SHORT" and (rsi < 30 or ema_short > ema_long):
                    action = "CLOSE"

            # 2. Execute Action
            if action == "BUY" and position is None:
                position = "LONG"
                entry_price = current_candle["close"]
                entry_time = current_candle["timestamp"]
            elif action == "SELL" and position is None:
                position = "SHORT"
                entry_price = current_candle["close"]
                entry_time = current_candle["timestamp"]
            elif action == "CLOSE" and position is not None:
                pnl = 0
                if position == "LONG":
                    pnl = (current_candle["close"] - entry_price) / entry_price * balance
                else:
                    pnl = (entry_price - current_candle["close"]) / entry_price * balance
                
                balance += pnl
                trades.append({
                    "symbol": symbol,
                    "entry_price": entry_price,
                    "exit_price": current_candle["close"],
                    "pnl": pnl,
                    "side": position,
                    "entry_time": entry_time.isoformat() if isinstance(entry_time, datetime) else entry_time,
                    "exit_time": current_candle["timestamp"].isoformat() if isinstance(current_candle["timestamp"], datetime) else current_candle["timestamp"]
                })
                position = None

            # Track equity (realized balance)
            equity_history.append({
                "time": current_candle["timestamp"].isoformat() if isinstance(current_candle["timestamp"], datetime) else current_candle["timestamp"],
                "value": balance
            })

        # 3. Final aggregation of stats
        stats = self._calculate_stats([e["value"] for e in equity_history], trades)
        stats["equity_curve"] = equity_history
        stats["trades"] = trades
        return stats

    def _calculate_stats(self, equity: List[float], trades: List[Dict]) -> Dict[str, Any]:
        """Hitung metrik performa profesional."""
        if not equity: return {}
        
        returns = pd.Series(equity).pct_change().dropna()
        
        sharpe = 0.0
        if not returns.empty and returns.std() > 0:
            sharpe = (returns.mean() / returns.std()) * np.sqrt(365 * 24)
            
        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / peak
        max_dd = drawdown.max() if not drawdown.empty else 0
        
        wins = [t for t in trades if t["pnl"] > 0]
        
        return {
            "total_return_pct": round(((equity[-1] - equity[0]) / equity[0] * 100), 2) if len(equity) > 1 else 0,
            "sharpe_ratio": round(float(sharpe), 2),
            "max_drawdown_pct": round(float(max_dd) * 100, 2),
            "final_balance": round(equity[-1], 2),
            "total_trades": len(trades),
            "win_rate": round(len(wins) / len(trades) * 100, 2) if trades else 0
        }
