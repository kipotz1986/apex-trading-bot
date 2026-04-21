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

class RiskGuard:
    """Service untuk validasi mikro risiko per-trade."""

    MAX_PER_TRADE_PCT = 5.0
    MAX_TOTAL_EXPOSURE_PCT = 20.0
    CONSECUTIVE_LOSS_LIMIT = 5

    def __init__(self, db: Session):
        self.db = db

    async def calculate_safe_size(self, proposed_size_usd: float, current_equity: float) -> float:
        """
        Hitung ukuran posisi yang aman berdasarkan batasan exposure.
        """
        if current_equity <= 0: return 0.0

        # 1. 5% per trade limit
        max_per_trade = current_equity * (self.MAX_PER_TRADE_PCT / 100)
        
        # 2. 20% total exposure limit
        max_total = current_equity * (self.MAX_TOTAL_EXPOSURE_PCT / 100)
        current_exposure = self._get_current_exposure()
        available_total = max(0, max_total - current_exposure)
        
        # 3. Consecutive Loss Multiplier
        multiplier = self._get_consecutive_loss_multiplier()
        
        final_size = min(proposed_size_usd, max_per_trade, available_total) * multiplier
        
        logger.info("safe_size_calculated", 
                    proposed=proposed_size_usd, final=final_size, multiplier=multiplier)
        return round(final_size, 2)

    def validate_correlation(self, symbol: str, side: str) -> bool:
        """
        Cek korelasi (Simpel: Tidak boleh ada 2 posisi LONG pada koin yang berkorelasi tinggi).
        Untuk saat ini: Mencegah membuka 2 koin Major ke arah yang sama jika sudah ada exposure.
        """
        # Hardcoded correlation groups for MVP
        corps = {
            "BTC/USDT": ["ETH/USDT", "SOL/USDT", "BNB/USDT"],
            "ETH/USDT": ["BTC/USDT", "SOL/USDT"]
        }
        
        active_symbols = self.db.query(Order.symbol).filter(Order.status == "FILLED", Order.closed_at == None).all()
        active_symbols = [s[0] for s in active_symbols]
        
        related = corps.get(symbol, [])
        for r in related:
            if r in active_symbols:
                logger.warning("correlation_blocked", symbol=symbol, related=r)
                return False
        return True

    def _get_current_exposure(self) -> float:
        """Hitung total nilai USD posisi yang terbuka."""
        exposure = self.db.query(Order.requested_amount * Order.average_filled_price).filter(
            Order.status == "FILLED",
            Order.closed_at == None
        ).all()
        return sum([e[0] or 0 for e in exposure])

    def _get_consecutive_loss_multiplier(self) -> float:
        """Kembalikan multiplier 0.5 jika loss beruntun >= 5."""
        state = self.db.query(RiskState).first()
        if state and state.consecutive_losses >= self.CONSECUTIVE_LOSS_LIMIT:
            return 0.5
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
