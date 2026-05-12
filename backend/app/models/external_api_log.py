from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from app.core.database import Base
from datetime import datetime

class ExternalApiLog(Base):
    __tablename__ = "external_api_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Logical FK to integration_logs (composite PK workaround)
    integration_log_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    url = Column(String, nullable=True)
    request_body = Column(Text, nullable=True)
    response_body = Column(Text, nullable=True)
    
    method = Column(String, nullable=True)  # GET, POST, etc
    headers = Column(Text, nullable=True)

    # Index for fast lookup by integration_log_id
    __table_args__ = (
        Index("ix_external_api_logs_integration_id", "integration_log_id"),
    )
