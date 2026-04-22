from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from app.core.database import Base
from datetime import datetime

class IntegrationLog(Base):
    __tablename__ = "integration_logs"

    # For TimescaleDB hypertables, the partitioning column (timestamp) 
    # must be part of any unique index, including the primary key.
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, primary_key=True, default=datetime.utcnow)
    
    service_type = Column(String, nullable=False)  # EXCHANGE, AI_PROVIDER, DATA_FEED
    provider_name = Column(String, nullable=False) # BINANCE, OPENAI, etc
    endpoint = Column(String, nullable=False)
    status = Column(String, nullable=False)        # SUCCESS, ERROR
    latency_ms = Column(Integer)
    error_details = Column(Text, nullable=True)

    # Index for filtering performance
    __table_args__ = (
        Index("ix_integration_logs_service_status", "service_type", "status"),
    )
