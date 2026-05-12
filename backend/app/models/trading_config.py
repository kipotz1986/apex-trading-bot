from sqlalchemy import Column, String, Boolean, Integer, DateTime
from datetime import datetime
from app.core.database import Base

class TradingConfig(Base):
    """Store which symbols are enabled for trading."""
    __tablename__ = "trading_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)  # e.g., "BTC/USDT:USDT"
    enabled = Column(Boolean, default=True)
    min_balance_usd = Column(Integer, default=100)
    priority = Column(Integer, default=0)  # For ordering
    created_at = Column(DateTime, default=datetime.utcnow)
