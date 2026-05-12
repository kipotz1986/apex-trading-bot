from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.schemas.trade_decision import TradeDecision
from app.schemas.portfolio import PortfolioState
from app.services.risk.circuit_breaker import CircuitBreaker
from app.services.risk.risk_guard import RiskGuard
from app.models.system_settings import SystemSettings
from app.core.logging import get_logger

logger = get_logger(__name__)


class PreTradeValidator:
    """Service untuk validasi ketat sebelum eksekusi trade."""

    def __init__(self, db: Session):
        self.db = db
        self.circuit_breaker = CircuitBreaker(db)
        self.risk_guard = RiskGuard(db)

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
            # 1. Global Circuit Breaker Check
            is_triggered, cb_reason = await self.circuit_breaker.check_all(portfolio.total_equity)
            if is_triggered:
                return False, f"CIRCUIT BREAKER: {cb_reason}"

            # 2. Level Action Check
            if decision.action == "HOLD":
                return False, "Action is HOLD, no execution needed."

            # 3. Position Sizing & Exposure Rules
            safe_size = await self.risk_guard.calculate_safe_size(
                decision.position_size_usd, portfolio.total_equity
            )
            min_trade_size = float(SystemSettings.get_value(self.db, "min_trade_size_usd", "10.0"))
            if safe_size < min_trade_size:
                return False, f"Calculated safe size too small: ${safe_size} (min: ${min_trade_size})"
            
            # Update decision size to safe size
            decision.position_size_usd = safe_size

            # 4. Correlation Guard
            side = "BUY" if "LONG" in decision.action else "SELL"
            if not self.risk_guard.validate_correlation(decision.symbol, side):
                return False, f"REJECTED BY CORRELATION GUARD for {decision.symbol}"

            # 5. Check Sufficient Balance (Margin)
            if decision.position_size_usd > portfolio.available_margin:
                return False, f"Insufficient margin. Required: ${decision.position_size_usd}, Available: ${portfolio.available_margin}"

            # 6. Check Confidence Threshold (Safe Guard) — aggressive default
            min_confidence = float(SystemSettings.get_value(self.db, "consensus_threshold_moderate", "0.15"))
            if decision.confidence < min_confidence:
                return False, f"Confidence too low for execution: {decision.confidence:.3f} (min: {min_confidence})"

            # 7. Check Spread (Anti-slippage) - Simplified as requested_price is not in schema
            # We skip this for now or could implement based on market_price vs some other reference

            logger.info("pre_trade_validation_passed", symbol=decision.symbol, amount=decision.position_size_usd)
            return True, ""

        except Exception as e:
            logger.error("pre_trade_validation_error", error=str(e))
            return False, f"Internal validation error: {str(e)}"
