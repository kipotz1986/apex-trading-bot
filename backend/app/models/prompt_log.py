from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from app.core.database import Base
from datetime import datetime

class PromptLog(Base):
    __tablename__ = "prompt_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Logical FK to integration_logs (which uses composite PK with timestamp)
    integration_log_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    prompt_input = Column(Text, nullable=True)
    prompt_output = Column(Text, nullable=True)
    model_name = Column(String, nullable=True)
    agent_name = Column(String, nullable=True, index=True)
    
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    # Index for fast lookup by integration_log_id
    __table_args__ = (
        Index("ix_prompt_logs_integration_id", "integration_log_id"),
    )
