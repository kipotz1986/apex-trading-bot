from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Index
from app.core.database import Base
from datetime import datetime

class IntegrationLog(Base):
    __tablename__ = "integration_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    service_type = Column(String, nullable=False)  # EXCHANGE, AI_PROVIDER, DATA_FEED
    provider_name = Column(String, nullable=False) # BINANCE, OPENAI, etc
    endpoint = Column(String, nullable=False)
    status = Column(String, nullable=False)        # SUCCESS, ERROR
    latency_ms = Column(Integer)
    error_details = Column(Text, nullable=True)

    # Index for rotation/cleanup performance
    __table_args__ = (
        Index("ix_integration_logs_timestamp_service", "timestamp", "service_type"),
    )
