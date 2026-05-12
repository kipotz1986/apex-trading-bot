"""
Position Monitor Service.

Monitors live (non-paper) open positions, updates floating PnL from exchange,
and triggers the learning pipeline when a live position is detected as closed
(SL/TP hit or manual close on the exchange side).

Paper trades are intentionally excluded here — they are handled by
ExecutionEngine.close_position(), which fires the learning event directly.
"""

import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.services.exchange import ExchangeService
from app.models.order import Order
from app.services.learning.pattern_memory import PatternMemory
from app.services.agent_scorer import AgentScorer
from app.core.logging import get_logger

logger = get_logger(__name__)


class PositionMonitor:
    """Service untuk monitoring posisi live aktif."""

    def __init__(self, exchange: ExchangeService, db: Session, pattern_memory: PatternMemory = None):
        self.exchange = exchange
        self.db = db
        self.pattern_memory = pattern_memory or PatternMemory()
        self.agent_scorer = AgentScorer(db)

    async def get_active_positions(self) -> List[Dict[str, Any]]:
        """Fetch open positions directly from the exchange."""
        try:
            positions = await self.exchange.exchange.fetch_positions()
            return [p for p in positions if float(p.get("contracts", 0)) > 0]
        except Exception as e:
            logger.error("fetch_active_positions_failed", error=str(e))
            return []

    async def sync_with_db(self):
        """
        Sync live positions against the exchange.

        - Paper orders are skipped — ExecutionEngine owns their lifecycle.
        - For live orders still open: refresh unrealised PnL.
        - For live orders no longer on exchange: mark CLOSED and fire learning.
        """
        active_exchange_pos = await self.get_active_positions()
        exchange_map = {p["symbol"]: p for p in active_exchange_pos}

        # Only sync LIVE, FILLED orders that have not been closed yet
        db_orders = (
            self.db.query(Order)
            .filter(
                Order.status == "FILLED",
                Order.closed_at == None,
                Order.is_paper == False,
            )
            .all()
        )

        for order in db_orders:
            if order.symbol in exchange_map:
                # Position still open — update floating PnL
                pos = exchange_map[order.symbol]
                order.pnl_usd = float(pos.get("unrealizedPnl") or 0.0)
                logger.debug("live_position_pnl_updated", symbol=order.symbol, pnl=order.pnl_usd)
            else:
                # Position no longer on exchange — closed by SL/TP or manually on exchange
                logger.info("live_position_closed_detected", symbol=order.symbol)
                order.status = "CLOSED"
                order.closed_at = datetime.now(timezone.utc)

                # Fire learning pipeline
                self._fire_learning_event(order)

        self.db.commit()

    # ------------------------------------------------------------------
    # Learning pipeline (mirrors ExecutionEngine._fire_learning_event)
    # ------------------------------------------------------------------

    def _fire_learning_event(self, order: Order):
        """
        Persist trade outcome to PatternMemory and update AgentScorer EMA.
        Called when a live position disappears from the exchange (SL/TP hit).
        """
        try:
            meta = order.meta_data or {}

            # 1. Store market-state fingerprint
            state_vector = meta.get("state_vector")
            if state_vector:
                outcome = "WIN" if (order.pnl_usd or 0) > 0 else "LOSS"
                self.pattern_memory.store_pattern(
                    vector=state_vector,
                    metadata={
                        "outcome": outcome,
                        "pnl": float(order.pnl_usd or 0.0),
                        "symbol": order.symbol,
                        "side": order.side,
                    },
                    pattern_id=f"trade_{order.id}_{int(datetime.now().timestamp())}",
                )
                logger.info("trade_outcome_learned", order_id=order.id, outcome=outcome)

            # 2. Update agent EMA scores
            signals = meta.get("agent_signals")
            if signals and isinstance(signals, dict):
                pnl_pct = 0.0
                notional = (order.requested_amount or 0) * (order.average_filled_price or 0)
                if notional > 0:
                    pnl_pct = (order.pnl_usd or 0.0) / notional * 100

                self.agent_scorer.update_performance({
                    "pnl_pct": pnl_pct,
                    "agent_signals": signals,
                    "is_neutral_win": False,
                })
                logger.info(
                    "agent_scores_updated_on_live_close",
                    order_id=order.id,
                    pnl_pct=round(pnl_pct, 4),
                )
        except Exception as e:
            logger.error("fire_learning_event_failed", order_id=order.id, error=str(e))
