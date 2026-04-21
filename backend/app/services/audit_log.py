"""
Audit Log Service.
Utility for recording system events.
"""

from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from app.core.logging import get_logger
from typing import Optional, Any, Dict

logger = get_logger(__name__)

def log_audit(
    db: Session,
    action: str,
    user: str,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """
    Creates an audit log entry in the database.
    """
    try:
        entry = AuditLog(
            user=user,
            action=action,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(entry)
        db.commit()
        logger.info("audit_log_created", action=action, user=user)
    except Exception as e:
        logger.error("audit_log_failed", error=str(e), action=action)
