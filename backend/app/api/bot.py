"""
Bot Control API Router.
"""

from fastapi import APIRouter, Depends, HTTPException, Body, Request
from sqlalchemy.orm import Session
from app.api import deps
from app.models.risk_state import RiskState
from app.services.audit_log import log_audit
from app.core.logging import get_logger
from datetime import datetime

logger = get_logger(__name__)
router = APIRouter()

@router.get("/status")
async def get_bot_status(
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """Returns the current bot operational status."""
    risk_state = db.query(RiskState).first()
    if not risk_state:
        raise HTTPException(status_code=404, detail="RiskState not initialized")
        
    return {
        "status": risk_state.system_status,
        "mode": "LIVE" if risk_state.is_live_enabled else "PAPER",
        "last_updated": risk_state.last_updated,
        "is_live_enabled": risk_state.is_live_enabled
    }

@router.post("/start")
async def start_bot(
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """Sets the system status to NORMAL."""
    risk_state = db.query(RiskState).first()
    risk_state.system_status = "NORMAL"
    db.commit()
    log_audit(db, "bot_start", current_user, ip_address=request.client.host)
    logger.info("bot_started_via_api", user=current_user)
    return {"message": "Bot started"}

@router.post("/stop")
async def stop_bot(
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """Sets the system status to PAUSED."""
    risk_state = db.query(RiskState).first()
    risk_state.system_status = "PAUSED"
    db.commit()
    log_audit(db, "bot_stop", current_user, ip_address=request.client.host)
    logger.info("bot_stopped_via_api", user=current_user)
    return {"message": "Bot paused"}

@router.post("/mode")
async def toggle_mode(
    request: Request,
    mode: str = Body(..., embed=True),
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """
    Switches between PAPER and LIVE trading.
    Includes safety checks for the 14-day trial period.
    """
    risk_state = db.query(RiskState).first()
    old_mode = "LIVE" if risk_state.is_live_enabled else "PAPER"
    
    if mode.upper() == "LIVE":
        # 14-day trial check
        days_passed = (datetime.utcnow() - risk_state.paper_trading_started_at).days
        if days_passed < 14:
            log_audit(db, "bot_mode_switch_rejected", current_user, {"reason": "trial_not_complete", "days": days_passed}, ip_address=request.client.host)
            raise HTTPException(
                status_code=403, 
                detail=f"Safety Lock: You must complete 14 days of Paper Trading. Remaining: {14 - days_passed} days."
            )
        risk_state.is_live_enabled = True
    else:
        risk_state.is_live_enabled = False
        
    db.commit()
    log_audit(db, "bot_mode_switch", current_user, {"from": old_mode, "to": mode.upper()}, ip_address=request.client.host)
    logger.info("bot_mode_changed", mode=mode, user=current_user)
    return {"mode": "LIVE" if risk_state.is_live_enabled else "PAPER"}
