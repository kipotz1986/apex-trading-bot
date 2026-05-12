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

def _get_risk_state(db: Session) -> RiskState:
    risk_state = db.query(RiskState).first()
    if not risk_state:
        raise HTTPException(status_code=503, detail="RiskState not initialized")
    return risk_state

@router.post("/start")
async def start_bot(
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """Sets the system status to NORMAL."""
    risk_state = _get_risk_state(db)
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
    risk_state = _get_risk_state(db)
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
    risk_state = _get_risk_state(db)
    old_mode = "LIVE" if risk_state.is_live_enabled else "PAPER"
    
    from app.models.exchange_credential import ExchangeCredential
    from app.core.encryption import decrypt
    from app.core.factory import ServiceFactory

    if mode.upper() == "LIVE":
        from app.models.system_settings import SystemSettings
        trial_days = int(SystemSettings.get_value(db, "paper_trial_days", "14"))
        days_passed = (datetime.utcnow() - risk_state.paper_trading_started_at).days
        if days_passed < trial_days:
            log_audit(db, "bot_mode_switch_rejected", current_user, {"reason": "trial_not_complete", "days": days_passed}, ip_address=request.client.host)
            raise HTTPException(
                status_code=403,
                detail=f"Safety Lock: You must complete {trial_days} days of Paper Trading. Remaining: {trial_days - days_passed} days."
            )

        cred = db.query(ExchangeCredential).filter_by(profile="live").first()
        if not cred or not cred.api_key:
            raise HTTPException(status_code=400, detail="Live credentials not configured. Go to Settings → Exchange → LIVE tab.")

        key = decrypt(cred.api_key)
        secret = decrypt(cred.api_secret)

        if not key or key.startswith("your_") or not secret or secret.startswith("your_"):
            raise HTTPException(status_code=400, detail="Live credentials are not set. Go to Settings → Exchange → LIVE tab.")

        # Pre-flight: test the live credentials against the real exchange BEFORE committing the switch
        from app.services.exchange import ExchangeService
        try:
            probe = ExchangeService(
                api_key=key,
                api_secret=secret,
                testnet=False,
                base_url=cred.base_url or None,
            )
            if cred.base_url and "api-demo.bybit.com" in cred.base_url:
                probe.exchange.enable_demo_trading(True)
            balance = await probe.get_balance()
            await probe.close()
            logger.info("live_credential_preflight_ok", profile="live")
        except Exception as e:
            err = str(e)
            logger.warning("live_credential_preflight_failed", error=err)
            raise HTTPException(
                status_code=400,
                detail=f"Live credentials rejected by exchange: {err}. Check your API key/secret in Settings → Exchange → LIVE tab."
            )

        if ServiceFactory._instance:
            await ServiceFactory._instance.exchange.switch_profile("live", key, secret, cred.base_url)

        risk_state.is_live_enabled = True
    else:
        cred = db.query(ExchangeCredential).filter_by(profile="demo").first()
        if cred and cred.api_key:
            key = decrypt(cred.api_key)
            secret = decrypt(cred.api_secret)
            if ServiceFactory._instance:
                await ServiceFactory._instance.exchange.switch_profile("demo", key, secret, cred.base_url)

        risk_state.is_live_enabled = False

    # Always clear equity immediately so old profile balance never persists
    risk_state.current_equity = 0
    db.commit()

    # Post-switch: sync balance from the new profile, clear price cache, broadcast WS event
    new_mode = "LIVE" if risk_state.is_live_enabled else "PAPER"
    new_equity = 0.0

    if ServiceFactory._instance:
        from app.services.market_stream import market_stream

        try:
            balance = await ServiceFactory._instance.exchange.get_balance()
            total_equity = 0.0
            if 'info' in balance and 'result' in balance['info'] and 'list' in balance['info']['result']:
                total_equity = float(balance['info']['result']['list'][0].get('totalEquity', 0.0))
            if total_equity <= 0 and 'total' in balance:
                total_equity = balance['total'].get('USDT', 0.0) + balance['total'].get('USDC', 0.0)
            risk_state.current_equity = total_equity
            db.commit()
            new_equity = total_equity
            logger.info("post_switch_balance_synced", mode=new_mode, equity=total_equity)
        except Exception as e:
            logger.warning("post_switch_balance_sync_failed", error=str(e))
            # equity stays 0 — correct for new/empty profile

        market_stream.last_prices.clear()

    from app.api.websocket import broadcast_updates
    await broadcast_updates("profile_switched", {
        "mode": new_mode,
        "equity": new_equity,
    })

    log_audit(db, "bot_mode_switch", current_user, {"from": old_mode, "to": mode.upper()}, ip_address=request.client.host)
    logger.info("bot_mode_changed", mode=mode, user=current_user)
    return {"mode": new_mode}
