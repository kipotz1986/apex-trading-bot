"""
Risk Guard Service.

Menerapkan aturan ukuran posisi, deteksi kerugian beruntun, 
dan pencegahan korelasi tinggi.
"""

from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.risk_state import RiskState
from app.models.order import Order
from app.core.logging import get_logger

logger = get_logger(__name__)

from app.models.system_settings import SystemSettings
# ... (rest of imports)

class RiskGuard:
    """Service untuk validasi mikro risiko per-trade."""

    # Very Aggressive defaults — large per-trade and total exposure ceilings
    DEFAULT_MAX_PER_TRADE_PCT = 20.0
    DEFAULT_MAX_TOTAL_EXPOSURE_PCT = 80.0
    CONSECUTIVE_LOSS_LIMIT = 8  # raised from 5 — keep firing through losing streaks

    def __init__(self, db: Session):
        self.db = db

    async def calculate_safe_size(self, proposed_size_usd: float, current_equity: float) -> float:
        """
        Hitung ukuran posisi yang aman berdasarkan batasan exposure.
        """
        if current_equity <= 0: return 0.0

        # Fetch limits from DB
        max_per_trade_pct = float(SystemSettings.get_value(self.db, "max_position_size", str(self.DEFAULT_MAX_PER_TRADE_PCT)))
        max_total_exposure_pct = float(SystemSettings.get_value(self.db, "max_total_exposure", str(self.DEFAULT_MAX_TOTAL_EXPOSURE_PCT)))

        # 1. Per trade limit
        max_per_trade = current_equity * (max_per_trade_pct / 100)
        
        # 2. Total exposure limit
        max_total = current_equity * (max_total_exposure_pct / 100)
        current_exposure = self._get_current_exposure()
        available_total = max(0, max_total - current_exposure)
        
        # 3. Consecutive Loss Multiplier
        multiplier = self._get_consecutive_loss_multiplier()
        
        final_size = min(proposed_size_usd, max_per_trade, available_total) * multiplier
        
        logger.info("safe_size_calculated", 
                    proposed=proposed_size_usd, final=final_size, multiplier=multiplier)
        return round(final_size, 2)

    # Correlation groups — symmetric map of high-correlation majors.
    # Built dynamically by exploding pairs into bidirectional lookups.
    _CORRELATION_GROUPS = [
        # Layer 1 majors move together
        {"BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT", "BNB/USDT:USDT"},
    ]

    @classmethod
    def _build_correlation_map(cls) -> Dict[str, List[str]]:
        """Build symmetric map: each symbol → list of correlated symbols (excluding itself)."""
        out: Dict[str, List[str]] = {}
        for group in cls._CORRELATION_GROUPS:
            for sym in group:
                out[sym] = [s for s in group if s != sym]
        return out

    def validate_correlation(self, symbol: str, side: str) -> bool:
        """
        Cek korelasi: cegah membuka 2+ posisi searah pada koin yang berkorelasi tinggi.
        Disabled by default in aggressive mode. Re-enabled by setting
        `correlation_guard_enabled=true` in SystemSettings.
        """
        if SystemSettings.get_value(self.db, "correlation_guard_enabled", "false").lower() != "true":
            return True

        corps = self._build_correlation_map()
        related = corps.get(symbol, [])
        if not related:
            return True  # Symbol not in any group — allow

        # Look up active positions of the SAME side; opposite-side positions are hedges, not stacked risk.
        active = (
            self.db.query(Order.symbol, Order.side)
            .filter(Order.status.in_(["OPEN", "FILLED"]), Order.closed_at == None)
            .all()
        )
        for active_sym, active_side in active:
            if active_sym in related and (active_side or "").upper() == side.upper():
                logger.warning("correlation_blocked", symbol=symbol, side=side, related=active_sym)
                return False
        return True

    def _get_current_exposure(self) -> float:
        """Hitung total nilai USD posisi yang terbuka."""
        exposure = self.db.query(Order).filter(
            Order.status == "FILLED",
            Order.closed_at == None
        ).all()
        return sum([(o.requested_amount or 0) * (o.average_filled_price or 0) for o in exposure])

    def _get_consecutive_loss_multiplier(self) -> float:
        """Returns a size multiplier based on consecutive loss streak — configurable via SystemSettings."""
        consecutive_loss_limit = int(SystemSettings.get_value(self.db, "consecutive_loss_limit", str(self.CONSECUTIVE_LOSS_LIMIT)))
        # Aggressive: only reduce to 0.8x (not 0.5x) after a long streak — keep trading
        consecutive_loss_multiplier = float(SystemSettings.get_value(self.db, "consecutive_loss_multiplier", "0.8"))
        state = self.db.query(RiskState).first()
        if state and state.consecutive_losses >= consecutive_loss_limit:
            return consecutive_loss_multiplier
        return 1.0

    def update_consecutive_losses(self, last_trade_pnl: float):
        """Update counter di DB."""
        state = self.db.query(RiskState).first()
        if not state: return

        if last_trade_pnl < 0:
            state.consecutive_losses += 1
        else:
            state.consecutive_losses = 0
        self.db.commit()
