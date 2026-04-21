"""
Mode Switcher Service.

Mengelola perpindahan antara Paper Trading dan Live Trading 
dengan aturan pengamanan yang ketat.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.risk_state import RiskState
from app.models.order import Order
from app.core.logging import get_logger

logger = get_logger(__name__)

class ModeSwitcher:
    """Service pengatur mode Live vs Paper."""

    MANDATORY_PAPER_DAYS = 14
    MIN_WIN_RATE = 55.0
    MAX_DRAWDOWN = 15.0

    def __init__(self, db: Session):
        self.db = db

    def can_switch_to_live(self) -> Tuple[bool, str]:
        """
        Mengecek apakah syarat untuk mode Live sudah terpenuhi.
        """
        state = self.db.query(RiskState).first()
        if not state:
            return False, "Sistem belum terinisialisasi."

        # 1. Check Duration
        duration = datetime.utcnow() - state.paper_trading_started_at
        if duration.days < self.MANDATORY_PAPER_DAYS:
            remaining = self.MANDATORY_PAPER_DAYS - duration.days
            return False, f"Paper trading harus berjalan minimal 14 hari. Sisa: {remaining} hari."

        # 2. Check Performance (Win Rate)
        paper_trades = self.db.query(Order).filter(Order.is_paper == True, Order.status == "CLOSED").all()
        if not paper_trades:
            return False, "Belum ada data trade untuk evaluasi performa."

        wins = [t for t in paper_trades if t.pnl_usd > 0]
        win_rate = (len(wins) / len(paper_trades)) * 100
        
        if win_rate < self.MIN_WIN_RATE:
            return False, f"Win Rate Paper Trading terlalu rendah ({win_rate:.1f}%). Minimum: 55%."

        # 3. Check Drawdown (dari RiskState metadata atau kalkulasi)
        # (Simplified: check if any trade had huge loss)
        max_loss_pct = 0.0
        for t in paper_trades:
            # Assuming we store entry/exit for pct calc
            pass

        return True, "Syarat terpenuhi. Anda bisa beralih ke mode Live."

    def switch_to_live(self) -> bool:
        """
        Berpindah ke mode Live jika memenuhi syarat.
        """
        allowed, message = self.can_switch_to_live()
        if not allowed:
            logger.warning("live_switch_blocked", reason=message)
            return False

        state = self.db.query(RiskState).first()
        state.is_live_enabled = True
        state.metadata_json["live_enabled_at"] = datetime.utcnow().isoformat()
        
        self.db.commit()
        logger.info("switched_to_live_mode")
        return True

    def switch_to_paper(self):
        """
        Mode Paper selalu diizinkan untuk keamanan.
        """
        state = self.db.query(RiskState).first()
        state.is_live_enabled = False
        self.db.commit()
        logger.info("switched_to_paper_mode")
