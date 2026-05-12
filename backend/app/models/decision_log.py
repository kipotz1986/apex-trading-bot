"""
Decision Log Model.

Menyimpan SETIAP keputusan orchestrator (termasuk HOLD)
agar AI Agents page bisa menampilkan aktivitas secara real-time.
"""

from sqlalchemy import Column, String, Float, DateTime, Integer, JSON
from datetime import datetime
from app.core.database import Base


class DecisionLog(Base):
    """Log keputusan multi-agent untuk dashboard AI Agents."""
    __tablename__ = "decision_logs"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    action = Column(String)            # HOLD | LONG | SHORT
    confidence = Column(Float, default=0.0)
    consensus_score = Column(Float, default=0.0)
    market_regime = Column(String, nullable=True)
    reasoning = Column(String, nullable=True)

    # Per-agent signals: {"technical": {"signal": "BUY", "confidence": 0.7}, ...}
    agent_signals = Column(JSON, default=dict)
    state_vector = Column(JSON, nullable=True) # Vector numerik untuk RL audit

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
