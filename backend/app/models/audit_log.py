"""
Audit Log Model.
Tracks administrative actions and security events.
"""

from sqlalchemy import Column, String, DateTime, Integer, JSON
from datetime import datetime
from app.core.database import Base

class AuditLog(Base):
    """Audit trail for critical system actions."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user = Column(String, index=True)
    action = Column(String, index=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
