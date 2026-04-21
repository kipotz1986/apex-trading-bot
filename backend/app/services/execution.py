"""
Order Execution Engine.

Bertanggung jawab untuk mengirim order ke exchange dan mengelola lifecycle order.
Mendukung Bybit (P0), Binance (P1) via CCXT.
"""

import asyncio
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.services.exchange import ExchangeService
from app.models.order import Order
from app.models.risk_state import RiskState
from app.services.paper_trading import PaperTradingEngine
from app.services.telegram import TelegramService
from app.core.logging import get_logger

logger = get_logger(__name__)


class ExecutionEngine:
    """Engine untuk eksekusi order kripto via CCXT."""

    def __init__(self, exchange: ExchangeService, db: Session, paper_engine: PaperTradingEngine, telegram: TelegramService = None):
        self.exchange = exchange
        self.db = db
        self.paper = paper_engine
        self.telegram = telegram or TelegramService()

    async def open_position(
        self,
        symbol: str,
        side: str,           # "BUY" (long) atau "SELL" (short)
        amount: float,       # Jumlah koin (e.g. 0.01 BTC)
        order_type: str = "MARKET",
        price: Optional[float] = None,
        leverage: int = 1,
        stop_loss: Optional[float] = None,
        take_profits: Optional[List[float]] = None,
        reasoning: str = ""
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
                    take_profits=take_profits, reasoning=reasoning
                )

            # --- LIVE EXECUTION LOGIC (Original) ---
            db_order = Order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                requested_amount=amount,
                requested_price=price,
                leverage=leverage,
                stop_loss_price=stop_loss,
                take_profit_prices=take_profits,
                reasoning=reasoning
            )
            self.db.add(db_order)
            self.db.commit()
            self.db.refresh(db_order)

            # 2. Set Leverage on Exchange
            try:
                await self.exchange.exchange.set_leverage(leverage, symbol)
            except Exception as le:
                logger.warning("failed_to_set_leverage", symbol=symbol, error=str(le))

            # 3. Kirim Order ke Exchange
            ccxt_side = side.lower()
            ccxt_type = order_type.lower()
            
            if ccxt_type == "market":
                order = await self.exchange.exchange.create_market_order(symbol, ccxt_side, amount)
            elif ccxt_type == "limit":
                if price is None: raise ValueError("Price required for limit order")
                order = await self.exchange.exchange.create_limit_order(symbol, ccxt_side, amount, price)
            else:
                raise ValueError(f"Unsupported order type: {order_type}")

            # 4. Update DB dengan data dari exchange
            db_order.exchange_order_id = order.get("id")
            db_order.status = "FILLED" if order.get("status") == "closed" else "OPEN"
            db_order.average_filled_price = order.get("average") or order.get("price")
            db_order.filled_amount = order.get("filled", 0.0)
            self.db.commit()

            logger.info("order_executed_successfully", order_id=db_order.exchange_order_id)

            # 5. Set Stop Loss dan Take Profit (Conditional Orders)
            if stop_loss:
                await self._set_stop_loss(symbol, side, amount, stop_loss)
            
            if take_profits:
                await self._set_take_profits(symbol, side, amount, take_profits)

            # Notify Telegram
            if self.telegram:
                asyncio.create_task(self.telegram.send_alert(
                    level="info",
                    title="POSITION OPENED",
                    body=f"Symbol: {symbol}\nSide: {side}\nPrice: ${db_order.average_filled_price:,.2f}\nAmount: {amount}\nSL: {stop_loss}"
                ))

            return db_order

        except Exception as e:
            logger.error("execution_failed", symbol=symbol, error=str(e))
            self.db.rollback()
            return None

    async def close_position(self, symbol: str, side: str, amount: float) -> bool:
        """Tutup posisi dengan membuka order ke arah berlawanan (ReduceOnly)."""
        try:
            close_side = "sell" if side.upper() == "BUY" else "buy"
            logger.info("closing_position", symbol=symbol, side=close_side, amount=amount)
            
            # Gunakan market order untuk close (ensure closure)
            res = await self.exchange.exchange.create_market_order(
                symbol, close_side, amount, params={"reduceOnly": True}
            )
            return res.get("status") in ["closed", "open"]
        except Exception as e:
            logger.error("close_position_failed", symbol=symbol, error=str(e))
            return False

    async def _set_stop_loss(self, symbol: str, side: str, amount: float, price: float):
        """Set stop loss order menggunakan native exchange trigger."""
        try:
            sl_side = "sell" if side.upper() == "BUY" else "buy"
            # Bybit/Binance params for trigger price
            params = {"reduceOnly": True, "stopPrice": price}
            
            await self.exchange.exchange.create_order(
                symbol, "stop", sl_side, amount, price, params=params
            )
            logger.info("stop_loss_triggered", symbol=symbol, price=price)
        except Exception as e:
            logger.error("set_stop_loss_failed", error=str(e))

    async def _set_take_profits(self, symbol: str, side: str, amount: float, prices: List[float]):
        """Set multi-level take profit orders."""
        try:
            tp_side = "sell" if side.upper() == "BUY" else "buy"
            per_level_amount = amount / len(prices)
            
            for price in prices:
                params = {"reduceOnly": True, "stopPrice": price}
                await self.exchange.exchange.create_order(
                    symbol, "limit", tp_side, per_level_amount, price, params=params
                )
                logger.info("take_profit_level_set", symbol=symbol, price=price)
        except Exception as e:
            logger.error("set_take_profit_failed", error=str(e))
