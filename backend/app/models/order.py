"""
Order Model.

Menyimpan lifecycle order dan status eksekusi di exchange.
"""

from sqlalchemy import Column, String, Float, DateTime, Integer, JSON, ForeignKey
from datetime import datetime
from app.core.database import Base

class Order(Base):
    """Data order yang dieksekusi di exchange."""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    side = Column(String)  # "BUY" | "SELL"
    order_type = Column(String)  # "MARKET" | "LIMIT"
    
    # Prices & Amounts
    requested_amount = Column(Float)
    filled_amount = Column(Float, default=0.0)
    requested_price = Column(Float, nullable=True) # Untuk LIMIT
    average_filled_price = Column(Float, nullable=True)
    
    # Status
    # OPEN | FILLED | CANCELED | REJECTED | EXPIRED
    status = Column(String, default="OPEN", index=True)
    
    # IDs from exchange
    exchange_order_id = Column(String, unique=True, index=True, nullable=True)
    client_order_id = Column(String, unique=True, index=True, nullable=True)
    
    # Risk parameters
    stop_loss_price = Column(Float, nullable=True)
    take_profit_prices = Column(JSON, default=list) # List of TP prices
    leverage = Column(Integer, default=1)
    
    # Results
    pnl_usd = Column(Float, default=0.0)
    fee_usd = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    
    # Traceability
    reasoning = Column(String, nullable=True)
    meta_data = Column(JSON, default=dict)
