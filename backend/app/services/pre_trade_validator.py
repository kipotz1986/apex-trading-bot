"""
Pre-Trade Validator.

Gerbang terakhir verifikasi sebelum order dikirim ke exchange.
Memastikan semua aturan risiko dan sistem dipenuhi.
"""

from typing import Dict, Any, Tuple
from app.schemas.trade_decision import TradeDecision
from app.schemas.portfolio import PortfolioState
from app.core.logging import get_logger

logger = get_logger(__name__)


class PreTradeValidator:
    """Service untuk validasi ketat sebelum eksekusi trade."""

    def __init__(self, settings: Any = None):
        self.settings = settings

    async def validate(
        self, 
        decision: TradeDecision, 
        portfolio: PortfolioState,
        market_price: float
    ) -> Tuple[bool, str]:
        """
        Validasi keputusan trade.
        Return: (is_valid, reason)
        """
        try:
            # 1. Check Action
            if decision.action == "HOLD":
                return False, "Action is HOLD, no execution needed."

            # 2. Check Sufficient Balance
            estimated_cost = decision.position_size_usd
            if estimated_cost > portfolio.available_margin:
                return False, f"Insufficient margin. Required: ${estimated_cost}, Available: ${portfolio.available_margin}"

            # 3. Check Confidence Threshold (Safe Guard)
            if decision.confidence < 0.4:
                return False, f"Confidence too low for execution: {decision.confidence}"

            # 4. Check Daily Loss Limit
            if portfolio.daily_pnl_pct <= -5.0:  # Hardcoded max 5% daily loss
                return False, f"Daily loss limit reached: {portfolio.daily_pnl_pct}%"

            # 5. Check Minimum Order Size (Exchange specific, but we check USD value)
            if estimated_cost < 10.0:  # Default min $10
                return False, f"Order size too small: ${estimated_cost}"

            # 6. Check Spread (Anti-slippage)
            # (Misal: market_price vs price di decision jika limit)
            if decision.requested_price:
                slippage = abs(decision.requested_price - market_price) / market_price
                if slippage > 0.02: # 2% max slippage guard
                    return False, f"Price slippage too high: {slippage:.2%}"

            logger.info("pre_trade_validation_passed", symbol=decision.symbol, amount=decision.position_size_usd)
            return True, ""

        except Exception as e:
            logger.error("pre_trade_validation_error", error=str(e))
            return False, f"Internal validation error: {str(e)}"
