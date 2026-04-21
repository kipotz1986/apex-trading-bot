"""
Risk State Model.

Menyimpan status risiko sistem, performa harian/mingguan, 
dan flag circuit breaker.
"""

from sqlalchemy import Column, String, Float, DateTime, Integer, JSON, Boolean
from datetime import datetime
from app.core.database import Base

class RiskState(Base):
    """Snapshot status risiko global bot."""
    __tablename__ = "risk_state"

    id = Column(Integer, primary_key=True)
    
    # Equity tracking
    current_equity = Column(Float, default=0.0)
    equity_peak = Column(Float, default=0.0) # Titik tertinggi untuk drawdown
    
    # Counters
    consecutive_losses = Column(Integer, default=0)
    total_trades_today = Column(Integer, default=0)
    
    # Circuit Breaker Status
    # NORMAL | PAUSED | REQUIRES_REVIEW | EMERGENCY_STOP
    system_status = Column(String, default="NORMAL")
    # Mode tracking
    is_live_enabled = Column(Boolean, default=False)
    paper_trading_started_at = Column(DateTime, default=datetime.utcnow)
    
    # Meta
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, default=dict)
