"""
Portfolio and PnL Data Router.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
from app.api import deps
from app.models.risk_state import RiskState
from app.models.risk_snapshot import RiskSnapshot
from app.models.order import Order
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("/summary")
async def get_portfolio_summary(
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """
    Returns current portfolio snapshot: Balance, Equity, PnL, Win Rate.
    """
    risk_state = db.query(RiskState).first()
    if not risk_state:
        # Fallback if no state initialized yet
        return {
            "balance": 0.0,
            "equity": 0.0,
            "unrealized_pnl": 0.0,
            "daily_pnl": 0.0,
            "total_trades": 0,
            "win_rate": 0.0
        }

    # Calculate Win Rate from closed orders
    closed_orders = db.query(Order).filter(Order.status == "CLOSED").all()
    wins = [o for o in closed_orders if (o.pnl_usd or 0.0) > 0]
    total = len(closed_orders)
    win_rate = (len(wins) / total * 100) if total > 0 else 0.0
    
    total_pnl = sum([o.pnl_usd or 0.0 for o in closed_orders])

    return {
        "balance": risk_state.current_equity, # Simplified: using equity as balance for now
        "equity": risk_state.current_equity,
        "unrealized_pnl": 0.0, # This would come from live position tracking
        "daily_pnl": 0.0, # Placeholder for today's PnL logic
        "total_pnl": total_pnl,
        "win_rate": round(win_rate, 2),
        "total_trades": total,
        "system_status": risk_state.system_status,
        "mode": "live" if risk_state.is_live_enabled else "paper"
    }

@router.get("/equity-history")
async def get_equity_history(
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """
    Returns time-series data for the equity curve chart.
    """
    snapshots = db.query(RiskSnapshot).order_by(RiskSnapshot.timestamp.asc()).all()
    
    return [
        {
            "time": s.timestamp.isoformat(),
            "equity": s.equity,
            "balance": s.balance
        }
        for s in snapshots
    ]
@router.get("/positions")
async def get_open_positions(
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """
    Returns all currently open positions (OPEN status).
    """
    positions = db.query(Order).filter(Order.status == "OPEN").all()
    
    return [
        {
            "id": p.id,
            "symbol": p.symbol,
            "side": p.side,
            "size": p.amount, # In USD/Contracts
            "entry": p.entry_price,
            "current": p.current_price or p.entry_price,
            "leverage": p.leverage,
            "pnl": p.pnl_usd or 0.0,
            "pnl_percent": ((p.current_price / p.entry_price - 1) * 100 * p.leverage) if p.entry_price and p.current_price else 0.0,
            "status": "profit" if (p.pnl_usd or 0.0) >= 0 else "loss"
        }
        for p in positions
    ]
