"""
Order Execution Engine.

Bertanggung jawab untuk mengirim order ke exchange dan mengelola lifecycle order.
Mendukung Bybit (P0), Binance (P1) via CCXT.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.services.exchange import ExchangeService
from app.models.order import Order
from app.models.risk_state import RiskState
from app.services.paper_trading import PaperTradingEngine
from app.services.telegram import TelegramService
from app.services.learning.pattern_memory import PatternMemory
from app.services.agent_scorer import AgentScorer
from app.core.logging import get_logger

logger = get_logger(__name__)


class ExecutionEngine:
    """Engine untuk eksekusi order kripto via CCXT."""

    def __init__(
        self,
        exchange: ExchangeService,
        db: Session,
        paper_engine: PaperTradingEngine,
        telegram: TelegramService = None,
        pattern_memory: PatternMemory = None,
        agent_scorer: AgentScorer = None,
    ):
        self.exchange = exchange
        self.db = db
        self.paper = paper_engine
        self.telegram = telegram or TelegramService()
        self.pattern_memory = pattern_memory or PatternMemory()
        self.agent_scorer = agent_scorer or AgentScorer(db)

    # ------------------------------------------------------------------
    # Learning pipeline — called after every position close
    # ------------------------------------------------------------------

    def _fire_learning_event(self, order: Order):
        """
        Persist trade outcome to PatternMemory (ChromaDB) and update
        AgentScorer EMA weights. Called synchronously after every close so
        that both paper and live paths feed the learning curve equally.
        """
        try:
            meta = order.meta_data or {}

            # 1. Store market-state fingerprint in ChromaDB
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
                    pattern_id=f"trade_{order.id}_{int(datetime.now(timezone.utc).timestamp())}",
                )
                logger.info("trade_pattern_stored", order_id=order.id, outcome=outcome)

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
                    "agent_scores_updated_on_close",
                    order_id=order.id,
                    pnl_pct=round(pnl_pct, 4),
                )
        except Exception as e:
            logger.error("fire_learning_event_failed", order_id=order.id, error=str(e))

    # ------------------------------------------------------------------
    # Open position
    # ------------------------------------------------------------------

    async def open_position(
        self,
        symbol: str,
        side: str,
        amount: float,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        leverage: int = 1,
        stop_loss: Optional[float] = None,
        take_profits: Optional[List[float]] = None,
        reasoning: str = "",
        state_vector: Optional[List[float]] = None,
        agent_signals: Optional[Dict[str, str]] = None,
    ) -> Optional[Order]:
        """
        Buka posisi baru.
        Mencakup: Set leverage, Create order, Log to DB, Set SL/TP.
        """
        try:
            logger.info("request_open_position", symbol=symbol, side=side, amount=amount, type=order_type)

            # Check Global Mode
            risk_state = self.db.query(RiskState).first()
            is_live = risk_state.is_live_enabled if risk_state else False

            if not is_live:
                logger.info("routing_to_paper_engine")
                return await self.paper.execute_virtual_order(
                    symbol=symbol, side=side, amount=amount, price=price,
                    leverage=leverage, stop_loss=stop_loss,
                    take_profits=take_profits, reasoning=reasoning,
                    state_vector=state_vector, agent_signals=agent_signals,
                )

            # --- LIVE EXECUTION LOGIC ---
            db_order = Order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                requested_amount=amount,
                requested_price=price,
                leverage=leverage,
                stop_loss_price=stop_loss,
                take_profit_prices=take_profits,
                reasoning=reasoning,
                meta_data={
                    "state_vector": state_vector,
                    "agent_signals": agent_signals or {},
                },
            )
            self.db.add(db_order)
            self.db.commit()
            self.db.refresh(db_order)

            # Set Leverage on Exchange
            try:
                await self.exchange.exchange.set_leverage(leverage, symbol)
            except Exception as le:
                logger.warning("failed_to_set_leverage", symbol=symbol, error=str(le))

            # Send Order to Exchange
            ccxt_side = side.lower()
            ccxt_type = order_type.lower()

            if ccxt_type == "market":
                order = await self.exchange.exchange.create_market_order(symbol, ccxt_side, amount)
            elif ccxt_type == "limit":
                if price is None:
                    raise ValueError("Price required for limit order")
                order = await self.exchange.exchange.create_limit_order(symbol, ccxt_side, amount, price)
            else:
                raise ValueError(f"Unsupported order type: {order_type}")

            # Update DB with exchange response
            db_order.exchange_order_id = order.get("id")
            db_order.status = "FILLED" if order.get("status") == "closed" else "OPEN"
            db_order.average_filled_price = order.get("average") or order.get("price")
            db_order.filled_amount = order.get("filled", 0.0)

            # Fallback: fetch order if price missing (Bybit market orders)
            if not db_order.average_filled_price and db_order.exchange_order_id:
                logger.info("price_missing_fetching_order", order_id=db_order.exchange_order_id)
                await asyncio.sleep(0.5)
                try:
                    fetched = await self.exchange.exchange.fetch_order(
                        db_order.exchange_order_id, symbol, params={"acknowledged": True}
                    )
                    db_order.average_filled_price = fetched.get("average") or fetched.get("price") or 0.0
                    db_order.filled_amount = fetched.get("filled", 0.0)
                    db_order.status = "FILLED" if fetched.get("status") == "closed" else "OPEN"
                except Exception as fe:
                    logger.warning("failed_to_fetch_order_details", order_id=db_order.exchange_order_id, error=str(fe))

            self.db.commit()
            logger.info("order_executed_successfully", order_id=db_order.exchange_order_id, price=db_order.average_filled_price)

            # --- REAL-TIME WEBSOCKET UPDATE ---
            try:
                from app.api.websocket import broadcast_updates
                asyncio.create_task(broadcast_updates("position_update", {
                    "type": "opened",
                    "position": {
                        "id": db_order.id,
                        "symbol": db_order.symbol,
                        "side": db_order.side,
                        "size": db_order.requested_amount,
                        "entry": db_order.average_filled_price or 0.0,
                        "current": db_order.average_filled_price or 0.0,
                        "leverage": db_order.leverage,
                        "pnl": 0.0,
                        "pnl_percent": 0.0,
                        "status": "profit"
                    }
                }))
            except Exception as we:
                logger.warning("websocket_broadcast_failed", error=str(we))

            # Set SL / TP
            if stop_loss:
                await self._set_stop_loss(symbol, side, amount, stop_loss)
            if take_profits:
                await self._set_take_profits(symbol, side, amount, take_profits)

            # Telegram notification
            if self.telegram:
                price_str = f"${db_order.average_filled_price:,.2f}" if db_order.average_filled_price else "PENDING"
                asyncio.create_task(self.telegram.send_alert(
                    level="info",
                    title="POSITION OPENED",
                    body=f"Symbol: {symbol}\nSide: {side}\nPrice: {price_str}\nAmount: {amount}\nSL: {stop_loss}",
                ))

            return db_order

        except Exception as e:
            logger.error("execution_failed", symbol=symbol, error=str(e))
            self.db.rollback()
            return None

    # ------------------------------------------------------------------
    # Close position
    # ------------------------------------------------------------------

    async def close_position(self, symbol: str, side: str, amount: float, order_id: Optional[int] = None) -> bool:
        """Tutup posisi dengan membuka order ke arah berlawanan (ReduceOnly)."""
        try:
            db_order = None
            if order_id:
                db_order = self.db.query(Order).filter(Order.id == order_id).first()

            if not db_order:
                db_order = self.db.query(Order).filter(
                    Order.symbol == symbol,
                    Order.status.in_(["OPEN", "FILLED"]),
                    Order.side == side.upper(),
                ).order_by(Order.created_at.desc()).first()

            if not db_order:
                logger.warning("close_position_no_order_found", symbol=symbol, order_id=order_id)
                return False

            is_paper_order = db_order.is_paper
            close_side = "sell" if side.upper() == "BUY" else "buy"

            # ---- PAPER CLOSE ----
            if is_paper_order:
                logger.info("close_position_paper_mode", symbol=symbol, order_id=db_order.id)
                db_order.status = "CLOSED"
                db_order.closed_at = datetime.now(timezone.utc).replace(tzinfo=None)

                close_price = await self._get_current_price(symbol)
                if close_price and db_order.average_filled_price:
                    price_ratio = close_price / db_order.average_filled_price
                    direction = 1 if side.upper() == "BUY" else -1
                    db_order.pnl_usd = (
                        (price_ratio - 1)
                        * direction
                        * (db_order.filled_amount or db_order.requested_amount or 0)
                        * close_price
                        * (db_order.leverage or 1)
                    )

                self.db.commit()

                # --- REAL-TIME WEBSOCKET UPDATE ---
                try:
                    from app.api.websocket import broadcast_updates
                    asyncio.create_task(broadcast_updates("position_update", {
                        "type": "closed",
                        "position_id": db_order.id,
                        "symbol": symbol
                    }))
                except Exception as we:
                    logger.warning("websocket_broadcast_failed", error=str(we))

                # Fire learning pipeline for paper trades
                self._fire_learning_event(db_order)

                # Telegram notification
                if self.telegram:
                    pnl_str = f"{'+' if (db_order.pnl_usd or 0) >= 0 else ''}${(db_order.pnl_usd or 0):.2f}"
                    asyncio.create_task(self.telegram.send_alert(
                        level="info",
                        title="PAPER POSITION CLOSED",
                        body=f"Symbol: {symbol}\nSide: {side}\nPnL: {pnl_str}",
                    ))

                return True

            # ---- LIVE CLOSE ----
            logger.info("closing_live_position", symbol=symbol, side=close_side, amount=amount)
            res = await self.exchange.exchange.create_market_order(
                symbol, close_side, amount, params={"reduceOnly": True}
            )

            success = res.get("status") in ["closed", "open"]

            if success:
                db_order.status = "CLOSED"
                db_order.closed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                if res.get("average") and db_order.average_filled_price and db_order.average_filled_price > 0:
                    db_order.pnl_usd = (
                        (res["average"] / db_order.average_filled_price - 1)
                        * db_order.requested_amount
                        * db_order.leverage
                        * (1 if side.upper() == "BUY" else -1)
                    )

                self.db.commit()
                logger.info("db_order_marked_closed", symbol=symbol, order_id=db_order.id)

                # --- REAL-TIME WEBSOCKET UPDATE ---
                try:
                    from app.api.websocket import broadcast_updates
                    asyncio.create_task(broadcast_updates("position_update", {
                        "type": "closed",
                        "position_id": db_order.id,
                        "symbol": symbol
                    }))
                except Exception as we:
                    logger.warning("websocket_broadcast_failed", error=str(we))

                # Fire learning pipeline for live trades
                self._fire_learning_event(db_order)

                # Telegram notification
                if self.telegram:
                    pnl_str = f"{'+' if (db_order.pnl_usd or 0) >= 0 else ''}${(db_order.pnl_usd or 0):.2f}"
                    asyncio.create_task(self.telegram.send_alert(
                        level="info",
                        title="LIVE POSITION CLOSED",
                        body=f"Symbol: {symbol}\nSide: {side}\nPnL: {pnl_str}",
                    ))

            return success

        except Exception as e:
            logger.error("close_position_failed", symbol=symbol, error=str(e))
            return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_current_price(self, symbol: str) -> Optional[float]:
        try:
            ticker = await self.exchange.exchange.fetch_ticker(symbol)
            return float(ticker.get("last") or ticker.get("close") or 0.0) or None
        except Exception:
            return None

    async def _set_stop_loss(self, symbol: str, side: str, amount: float, price: float):
        """Set stop loss order via exchange trigger."""
        try:
            sl_side = "sell" if side.upper() == "BUY" else "buy"
            params = {"reduceOnly": True, "stopPrice": price}
            await self.exchange.exchange.create_order(symbol, "stop", sl_side, amount, price, params=params)
            logger.info("stop_loss_set", symbol=symbol, price=price)
        except Exception as e:
            logger.error("set_stop_loss_failed", error=str(e))

    async def _set_take_profits(self, symbol: str, side: str, amount: float, prices: List[float]):
        """Set multi-level take profit orders."""
        try:
            tp_side = "sell" if side.upper() == "BUY" else "buy"
            per_level = amount / len(prices)
            for price in prices:
                params = {"reduceOnly": True, "stopPrice": price}
                await self.exchange.exchange.create_order(symbol, "limit", tp_side, per_level, price, params=params)
                logger.info("take_profit_set", symbol=symbol, price=price)
        except Exception as e:
            logger.error("set_take_profit_failed", error=str(e))
