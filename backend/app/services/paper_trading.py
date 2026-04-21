"""
Paper Trading Engine.

Simulasi eksekusi trade menggunakan data real-time namun tanpa 
risiko uang sungguhan. Meniru perilaku exchange API.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.order import Order
from app.core.logging import get_logger
import uuid
import datetime

logger = get_logger(__name__)

class PaperTradingEngine:
    """Simulator eksekusi order."""

    # Simulasi biaya dan slippage
    FEE_PCT = 0.001 # 0.1%
    SLIPPAGE_PCT = 0.0005 # 0.05% for MARKET orders

    def __init__(self, db: Session):
        self.db = db

    async def execute_virtual_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        leverage: int = 1,
        stop_loss: float = None,
        take_profits: List[float] = None,
        reasoning: str = ""
    ) -> Order:
        """
        Mensimulasikan eksekusi order dan menyimpannya ke database.
        """
        # 1. Hitung Slippage (Hanya untuk Market Order simulasi)
        slippage = price * self.SLIPPAGE_PCT
        fill_price = price + slippage if side == "BUY" else price - slippage
        
        # 2. Hitung Fee
        fee = amount * fill_price * self.FEE_PCT
        
        # 3. Create Order Record
        order = Order(
            symbol=symbol,
            side=side,
            order_type="MARKET",
            requested_amount=amount,
            filled_amount=amount,
            average_filled_price=fill_price,
            status="FILLED", # Langsung filled di simulator
            exchange_order_id=f"paper-{uuid.uuid4().hex[:8]}",
            leverage=leverage,
            stop_loss_price=stop_loss,
            take_profit_prices=take_profits or [],
            fee_usd=fee,
            is_paper=True,
            is_testnet=False,
            reasoning=reasoning
        )
        
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        
        logger.info("paper_order_filled", symbol=symbol, side=side, price=fill_price)
        return order

    async def simulate_closure(self, order: Order, exit_price: float, reason: str = "SL_TP"):
        """
        Mensimulasikan penutupan posisi.
        """
        # Hitung PnL
        if order.side == "BUY":
            pnl = (exit_price - order.average_filled_price) * order.requested_amount * order.leverage
        else:
            pnl = (order.average_filled_price - exit_price) * order.requested_amount * order.leverage
            
        # Kurangi fee penutupan
        close_fee = order.requested_amount * exit_price * self.FEE_PCT
        
        order.pnl_usd = pnl - order.fee_usd - close_fee
        order.status = "CLOSED"
        order.closed_at = datetime.datetime.utcnow()
        order.meta_data["close_reason"] = reason
        
        self.db.commit()
        logger.info("paper_position_closed", symbol=order.symbol, pnl=order.pnl_usd)
