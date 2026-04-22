"""
System Settings API Router.
"""

from fastapi import APIRouter, Depends, HTTPException, Body, Request
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.api import deps
from app.core.config import settings
from app.services.audit_log import log_audit
from app.core.logging import get_logger

from app.models.audit_log import AuditLog
from sqlalchemy import desc

logger = get_logger(__name__)
router = APIRouter()

@router.get("/audit-logs")
async def get_audit_logs(
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user),
    limit: int = 50
):
    """Returns the most recent audit logs."""
    logs = db.query(AuditLog).order_by(desc(AuditLog.timestamp)).limit(limit).all()
    return logs

@router.get("/")
async def get_all_settings(
    current_user: str = Depends(deps.get_current_user)
):
    """
    Returns application settings. 
    Sensitive keys like API keys are masked.
    """
    return {
        "ai": {
            "provider": settings.AI_PROVIDER,
            "model": settings.AI_MODEL,
            "api_key": "****" if settings.AI_API_KEY else ""
        },
        "exchange": {
            "name": settings.EXCHANGE_NAME,
            "api_key": "****" if settings.EXCHANGE_API_KEY else "",
            "testnet": settings.EXCHANGE_TESTNET
        },
        "app": {
            "env": settings.APP_ENV,
            "timezone": settings.TIMEZONE
        }
    }

@router.put("/ai")
async def update_ai_settings(
    request: Request,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """Updates AI provider settings."""
    # In a real app, this would write to DB or .env
    log_audit(db, "settings_update_ai", current_user, payload, ip_address=request.client.host)
    logger.info("settings_updated_ai", user=current_user, provider=payload.get("provider"))
    return {"status": "success", "message": "AI settings updated (simulation)"}

@router.put("/risk")
async def update_risk_settings(
    request: Request,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """Updates risk management parameters."""
    log_audit(db, "settings_update_risk", current_user, payload, ip_address=request.client.host)
    logger.info("settings_updated_risk", user=current_user)
    return {"status": "success", "message": "Risk parameters updated (simulation)"}
