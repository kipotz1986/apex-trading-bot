"""
Candle database model.
Representing OHLCV data stored in TimescaleDB.
"""

from sqlalchemy import Column, DateTime, Float, String, Index, UniqueConstraint
from app.core.database import Base

class Candle(Base):
    """
    Model untuk menyimpan data candlestick (OHLCV).
    Akan dikonversi menjadi Hypertable di PostgreSQL oleh TimescaleDB.
    """
    __tablename__ = "candles"

    # Composite PK atau Timescale hypertable butuh kolom waktu sebagai bagian dari index
    # Catatan: SQLAlchemy butuh primary_key=True pada minimal satu kolom
    # Kita gunakan timestamp + symbol + timeframe sebagai identifikasi unik
    timestamp = Column(DateTime, primary_key=True, index=True)
    symbol = Column(String, primary_key=True, index=True)
    timeframe = Column(String, primary_key=True, index=True)
    
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)

    # Tambahan Index untuk query range cepat
    __table_args__ = (
        Index("idx_candle_symbol_timeframe_timestamp", "symbol", "timeframe", "timestamp"),
    )

    def to_dict(self):
        """Helper to convert model to dict."""
        return {
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume
        }
