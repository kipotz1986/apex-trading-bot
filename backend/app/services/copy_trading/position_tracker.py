"""
Position Tracker Service.

Memantau posisi aktif dari top traders dan mendeteksi perubahan (OPEN/CLOSE).
"""

import asyncio
from typing import List, Dict, Any, Set
from sqlalchemy.orm import Session
from app.models.copy_trade import TopTrader, CopyTradeEvent
from app.core.logging import get_logger

logger = get_logger(__name__)

class PositionTracker:
    """Service untuk tracking posisi trader secara real-time."""

    def __init__(self, db: Session):
        self.db = db
        # Cache internal untuk menyimpan posisi terakhir yang diketahui
        # {trader_id: {symbol: "BUY", ...}}
        self._last_positions: Dict[str, Dict[str, str]] = {}

    async def track_all(self):
        """Poll posisi untuk semua trader aktif di database."""
        traders = self.db.query(TopTrader).filter(TopTrader.is_active == True).all()
        
        for t in traders:
            await self._track_trader(t.trader_id)

    async def _track_trader(self, trader_id: str):
        """
        Ambil posisi saat ini dari exchange (mocked) 
        dan bandingkan dengan snapshot sebelumnya.
        """
        try:
            # 1. Fetch current positions from Exchange (Mocked)
            current_positions = await self._fetch_trader_positions_from_exchange(trader_id)
            
            # 2. Compare with internal cache
            previous_positions = self._last_positions.get(trader_id, {})
            
            # Detect OPENs (Ada di current tapi tidak ada di previous)
            for symbol, side in current_positions.items():
                if symbol not in previous_positions:
                    self._create_event(trader_id, symbol, side, "OPEN")
                elif previous_positions[symbol] != side:
                    # Ganti arah (e.g. LONG ke SHORT)
                    self._create_event(trader_id, symbol, previous_positions[symbol], "CLOSE")
                    self._create_event(trader_id, symbol, side, "OPEN")

            # Detect CLOSEs (Ada di previous tapi tidak ada di current)
            for symbol, side in previous_positions.items():
                if symbol not in current_positions:
                    self._create_event(trader_id, symbol, side, "CLOSE")

            # Update cache
            self._last_positions[trader_id] = current_positions
            
        except Exception as e:
            logger.error("position_tracking_failed", trader_id=trader_id, error=str(e))

    def _create_event(self, trader_id: str, symbol: str, side: str, event_type: str):
        """Simpan event ke database."""
        event = CopyTradeEvent(
            trader_id=trader_id,
            symbol=symbol,
            side=side,
            event_type=event_type,
            entry_price=60000.0, # Mock price
            size_usd=1000.0,
            metadata_json={"source": "poller"}
        )
        self.db.add(event)
        self.db.commit()
        logger.info("copy_trade_event_detected", 
                    trader_id=trader_id, symbol=symbol, type=event_type)

    async def _fetch_trader_positions_from_exchange(self, trader_id: str) -> Dict[str, str]:
        """
        Mock fetching positions. 
        In reality, this would use Bybit API / Web Request.
        """
        # Return {symbol: side}
        # T001 is BULLISH on BTC, T004 is BULLISH on ETH
        if trader_id == "T001":
            return {"BTC/USDT": "BUY"}
        if trader_id == "T004":
            return {"ETH/USDT": "BUY"}
        return {}
