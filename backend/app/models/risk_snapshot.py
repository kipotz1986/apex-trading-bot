"""
Risk Snapshot Model.
Stores historical snapshots of the bot's financial state for reporting and charting.
"""

from sqlalchemy import Column, Float, DateTime, Integer
from datetime import datetime
from app.core.database import Base

class RiskSnapshot(Base):
    """Historical snapshot of risk metrics."""
    __tablename__ = "risk_snapshots"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    equity = Column(Float, nullable=False)
    balance = Column(Float, nullable=False)
    drawdown_pct = Column(Float, default=0.0)
