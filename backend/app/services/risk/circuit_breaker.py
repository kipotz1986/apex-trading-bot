"""
Circuit Breaker Service.

Memonitor PnL dan Drawdown untuk menghentikan bot jika risiko terlalu tinggi.
"""

from typing import Tuple, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.risk_state import RiskState
from app.models.order import Order
from app.services.telegram import TelegramService
from app.core.logging import get_logger

logger = get_logger(__name__)

class CircuitBreaker:
    """Service untuk manajemen stop harian, mingguan, dan drawdown."""

    def __init__(self, db: Session, telegram: TelegramService = None):
        self.db = db
        self.telegram = telegram or TelegramService()

    async def check_all(self, current_equity: float) -> Tuple[bool, str]:
        """
        Cek semua parameter circuit breaker.
        Return: (is_triggered, reason)
        """
        state = self._get_or_create_state()
        
        # 1. Update Equity Peak & Drawdown
        if current_equity > state.equity_peak:
            state.equity_peak = current_equity
            self.db.commit()
            
        drawdown_pct = 0.0
        if state.equity_peak > 0:
            drawdown_pct = (state.equity_peak - current_equity) / state.equity_peak * 100
            
        if drawdown_pct >= 15.0:
            state.system_status = "EMERGENCY_STOP"
            self.db.commit()
            
            # Notify Telegram
            self._send_instant_alert("EMERGENCY_STOP", f"Max drawdown reached: {drawdown_pct:.2f}% (Limit: 15%)")
            
            return True, f"Max drawdown reached: {drawdown_pct:.2f}% (Limit: 15%)"

        # 2. Daily Loss Limit (3%)
        daily_pnl = self._calculate_realized_pnl(days=1)
        daily_loss_pct = (daily_pnl / current_equity) * 100 if current_equity > 0 else 0
        
        if daily_loss_pct <= -3.0:
            state.system_status = "PAUSED"
            state.paused_until = datetime.utcnow() + timedelta(hours=24)
            self.db.commit()
            return True, f"Daily loss limit reached: {daily_loss_pct:.2f}% (Limit: -3%)"

        # 3. Weekly Loss Limit (7%)
        weekly_pnl = self._calculate_realized_pnl(days=7)
        weekly_loss_pct = (weekly_pnl / current_equity) * 100 if current_equity > 0 else 0
        
        if weekly_loss_pct <= -7.0:
            state.system_status = "REQUIRES_REVIEW"
            self.db.commit()
            return True, f"Weekly loss limit reached: {weekly_loss_pct:.2f}% (Limit: -7%)"

        # 4. Check if currently paused
        if state.system_status == "PAUSED":
            if state.paused_until and datetime.utcnow() > state.paused_until:
                state.system_status = "NORMAL"
                self.db.commit()
                return False, ""
            return True, f"Bot is paused until {state.paused_until}"

        if state.system_status in ["REQUIRES_REVIEW", "EMERGENCY_STOP"]:
            return True, f"Bot is stopped due to {state.system_status} status."

        return False, ""

    def _get_or_create_state(self) -> RiskState:
        """Ambit atau buat status risiko tunggal."""
        state = self.db.query(RiskState).first()
        if not state:
            state = RiskState(equity_peak=0.0, system_status="NORMAL")
            self.db.add(state)
            self.db.commit()
            self.db.refresh(state)
        return state

    def _calculate_realized_pnl(self, days: int) -> float:
        """Hitung total profit/loss dari closed trades dalam X hari terakhir."""
        since = datetime.utcnow() - timedelta(days=days)
        total_pnl = self.db.query(func.sum(Order.pnl_usd)).filter(
            Order.status == "CLOSED",
            Order.closed_at >= since
        ).scalar() or 0.0
        return float(total_pnl)

    def _send_instant_alert(self, level: str, reason: str):
        """Helper untuk kirim alert tanpa blocking."""
        if self.telegram:
            import asyncio
            asyncio.create_task(self.telegram.send_alert(
                level="critical" if level in ["EMERGENCY_STOP", "REQUIRES_REVIEW"] else "warning",
                title=f"CIRCUIT BREAKER: {level}",
                body=f"Alasan: {reason}\nSistem telah dibatasi demi keamanan modal."
            ))
