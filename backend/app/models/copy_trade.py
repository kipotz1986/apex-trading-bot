"""
Copy Trading Models.

Menyimpan data top traders dan log aktivitas (events) mereka.
"""

from sqlalchemy import Column, String, Float, DateTime, Integer, JSON, Boolean, ForeignKey
from datetime import datetime
from app.core.database import Base

class TopTrader(Base):
    """Data trader terbaik dari exchange leaderboard."""
    __tablename__ = "top_traders"

    trader_id = Column(String, primary_key=True, index=True)
    username = Column(String)
    exchange = Column(String, default="bybit")
    
    # Stats
    roi_pct = Column(Float)
    win_rate_pct = Column(Float)
    pnl_usd = Column(Float)
    max_drawdown_pct = Column(Float)
    track_record_days = Column(Integer)
    followers_count = Column(Integer)
    
    # Meta
    composite_score = Column(Float, index=True)
    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime, default=datetime.utcnow)

class CopyTradeEvent(Base):
    """Log aktivitas buka/tutup posisi dari top trader."""
    __tablename__ = "copy_trade_events"

    id = Column(Integer, primary_key=True, index=True)
    trader_id = Column(String, ForeignKey("top_traders.trader_id"))
    symbol = Column(String, index=True)
    side = Column(String)  # "BUY" | "SELL"
    event_type = Column(String)  # "OPEN" | "CLOSE"
    
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    size_usd = Column(Float)
    
    timestamp = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(JSON, default=dict)
