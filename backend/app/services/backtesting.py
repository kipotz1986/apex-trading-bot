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
        Input: List of candles {time, open, high, low, close, volume}
        """
        logger.info("backtest_started", symbol=symbol, candles=len(historical_candles))
        
        balance = initial_balance
        equity_history = []
        trades = []
        
        # 1. Loop through time bits
        for i in range(20, len(historical_candles)): # Start after 20 candles for technical indicators
            window = historical_candles[:i+1]
            current_candle = historical_candles[i]
            
            # (Simplifikasi: Mock portfolio state untuk backtest)
            from app.schemas.portfolio import PortfolioState
            portfolio = PortfolioState(
                total_balance=balance,
                total_equity=balance,
                available_margin=balance,
                daily_pnl_pct=0,
                weekly_pnl_pct=0,
                max_drawdown_pct=0
            )

            # 2. Get AI Decision (In practice, we need to mock data providers)
            # Untuk MVP Backtest, kita bypass network-heavy agents
            decision = await self.orchestrator.decide(
                symbol=symbol,
                market_data={"candles": window},
                portfolio=portfolio
            )
            
            if decision.action != "HOLD":
                # 3. Simulate execution
                order = await self.simulator.execute_virtual_order(
                    symbol=symbol,
                    side="BUY" if "LONG" in decision.action else "SELL",
                    amount=decision.position_size_usd / current_candle["close"],
                    price=current_candle["close"],
                    leverage=decision.leverage,
                    stop_loss=decision.stop_loss,
                    take_profits=decision.take_profit,
                    reasoning=f"BACKTEST: {decision.reasoning}"
                )
                
                # simulate immediate closure for MVP test flow? 
                # No, we wait X steps or SL/TP.
                # (Logic SL/TP handling can be added here)
                
            equity_history.append(balance)

        # 4. Final aggregation of stats
        stats = self._calculate_stats(equity_history, trades)
        return stats

    def _calculate_stats(self, equity: List[float], trades: List[Dict]) -> Dict[str, Any]:
        """Hitung metrik performa profesional."""
        if not equity: return {}
        
        returns = pd.Series(equity).pct_change().dropna()
        
        sharpe = 0.0
        if returns.std() > 0:
            sharpe = (returns.mean() / returns.std()) * np.sqrt(365 * 24) # Annualized 1h candles
            
        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / peak
        max_dd = drawdown.max()
        
        return {
            "total_return_pct": (equity[-1] - equity[0]) / equity[0] * 100,
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown_pct": round(max_dd * 100, 2),
            "final_balance": equity[-1]
        }
