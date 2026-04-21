"""
Agent Score Model.
Menyimpan akurasi dan bobot setiap agent.
"""

from sqlalchemy import Column, String, Float, DateTime
from datetime import datetime
from app.core.database import Base

class AgentScore(Base):
    """Model untuk menyimpan performa dan bobot agen analis."""
    __tablename__ = "agent_scores"

    agent_name = Column(String, primary_key=True, index=True)
    score = Column(Float, default=100.0)  # Skor performa (ELO-like or straight accuracy)
    weight = Column(Float, default=0.25)  # Bobot voting (0.0 - 1.0)
    total_trades = Column(Float, default=0)
    successful_trades = Column(Float, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
