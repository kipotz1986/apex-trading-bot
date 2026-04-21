"""
System Settings API Router.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict, Any
from app.api import deps
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

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
    payload: Dict[str, Any] = Body(...),
    current_user: str = Depends(deps.get_current_user)
):
    """Updates AI provider settings."""
    # In a real app, this would write to DB or .env
    logger.info("settings_updated_ai", user=current_user, provider=payload.get("provider"))
    return {"status": "success", "message": "AI settings updated (simulation)"}

@router.put("/risk")
async def update_risk_settings(
    payload: Dict[str, Any] = Body(...),
    current_user: str = Depends(deps.get_current_user)
):
    """Updates risk management parameters."""
    logger.info("settings_updated_risk", user=current_user)
    return {"status": "success", "message": "Risk parameters updated (simulation)"}
