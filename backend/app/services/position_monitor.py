"""
Position Monitor Service.

Memantau posisi terbuka secara periodik, menghitung PnL floating,
dan mendeteksi perubahan status di exchange.
"""

import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.services.exchange import ExchangeService
from app.models.order import Order
from app.core.logging import get_logger

logger = get_logger(__name__)

class PositionMonitor:
    """Service untuk monitoring posisi aktif."""

    def __init__(self, exchange: ExchangeService, db: Session):
        self.exchange = exchange
        self.db = db

    async def get_active_positions(self) -> List[Dict[str, Any]]:
        """Ambil posisi terbuka langsung dari exchange."""
        try:
            # fetch_positions() adalah standard CCXT unified method
            positions = await self.exchange.exchange.fetch_positions()
            # Filter hanya positions yang tidak nol
            active = [p for p in positions if float(p.get("contracts", 0)) > 0]
            return active
        except Exception as e:
            logger.error("fetch_active_positions_failed", error=str(e))
            return []

    async def sync_with_db(self):
        """Singkronisasi status posisi di exchange dengan database."""
        active_exchange_pos = await self.get_active_positions()
        
        # Mapping symbol untuk memudahkan lookup
        exchange_map = {p["symbol"]: p for p in active_exchange_pos}
        
        # Ambil orders di DB yang statusnya OPEN/FILLED tapi belum ditutup
        db_orders = self.db.query(Order).filter(Order.status == "FILLED", Order.closed_at == None).all()
        
        for order in db_orders:
            if order.symbol in exchange_map:
                pos = exchange_map[order.symbol]
                # Update floating PnL
                order.pnl_usd = float(pos.get("unrealizedPnl", 0.0))
                logger.debug("position_updated", symbol=order.symbol, pnl=order.pnl_usd)
            else:
                # Posisi sudah tidak ada di exchange -> Berarti sudah ditutup (SL/TP hit atau manual)
                logger.info("position_closed_detected", symbol=order.symbol)
                order.status = "CLOSED"
                order.closed_at = datetime.now(timezone.utc)
                # Kita bisa mencoba fetch trades terakhir untuk PnL absolut jika perlu
        
        self.db.commit()
