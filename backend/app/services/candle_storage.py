"""
Candle Storage Service.
Menyimpan dan mengambil data candlestick dari TimescaleDB.
Menggunakan batch insert dan upsert logic.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from app.models.candle import Candle
from app.core.logging import get_logger

logger = get_logger(__name__)

class CandleStorageService:
    """Service untuk manajemen persistensi data candlestick."""

    def __init__(self, db: Session):
        self.db = db

    async def save_candles(self, symbol: str, timeframe: str, candles: List[Dict[str, Any]]) -> int:
        """
        Simpan list data candle ke database.
        Mendukung upsert (update if exists).
        
        Args:
            symbol: Trading pair
            timeframe: Periode candle
            candles: List of dict {timestamp, open, high, low, close, volume}
            
        Returns:
            Jumlah record yang diproses.
        """
        if not candles:
            return 0

        # Persiapkan data untuk batch insert
        stmt = insert(Candle)
        
        values = []
        for c in candles:
            values.append({
                "timestamp": c["timestamp"],
                "symbol": symbol,
                "timeframe": timeframe,
                "open": float(c["open"]),
                "high": float(c["high"]),
                "low": float(c["low"]),
                "close": float(c["close"]),
                "volume": float(c["volume"]),
            })

        # Logic Upsert: Jika (timestamp, symbol, timeframe) sudah ada, update harganya
        # Ini penting karena candle terbaru mungkin belum "close" sempurna
        stmt = stmt.values(values)
        update_stmt = stmt.on_conflict_do_update(
            index_elements=["timestamp", "symbol", "timeframe"],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
            }
        )

        try:
            self.db.execute(update_stmt)
            self.db.commit()
            logger.info("candles_saved_to_db", symbol=symbol, count=len(candles))
            return len(candles)
        except Exception as e:
            self.db.rollback()
            logger.error("candle_save_error", symbol=symbol, error=str(e))
            raise

    def get_candles(
        self, 
        symbol: str, 
        timeframe: str, 
        start_time: Optional[datetime] = None,
        limit: int = 500
    ) -> List[Candle]:
        """Ambil data candle dari database."""
        query = self.db.query(Candle).filter(
            Candle.symbol == symbol,
            Candle.timeframe == timeframe
        )
        
        if start_time:
            query = query.filter(Candle.timestamp >= start_time)
            
        return query.order_by(Candle.timestamp.asc()).limit(limit).all()

    def get_latest_timestamp(self, symbol: str, timeframe: str) -> Optional[datetime]:
        """Cek timestamp candle terakhir yang disimpan."""
        last_candle = self.db.query(Candle).filter(
            Candle.symbol == symbol,
            Candle.timeframe == timeframe
        ).order_by(Candle.timestamp.desc()).first()
        
        return last_candle.timestamp if last_candle else None
