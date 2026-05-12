from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from app.core.database import Base

class ExchangeCredential(Base):
    """Stores encrypted API credentials for exchange profiles (e.g., demo vs live)."""
    __tablename__ = "exchange_credentials"

    id = Column(Integer, primary_key=True)
    profile = Column(String, unique=True, index=True)  # "demo" | "live"
    exchange = Column(String, default="bybit")         # Exchange name
    api_key = Column(String)                           # Encrypted
    api_secret = Column(String)                        # Encrypted
    base_url = Column(String, nullable=True)           # Optional override URL
    is_active = Column(Boolean, default=False)         # Currently active profile
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
