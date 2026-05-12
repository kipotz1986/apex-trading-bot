"""
Trade History API Router.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from app.api import deps
from app.models.order import Order
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("/")
async def get_trade_history(
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    symbol: Optional[str] = None,
    side: Optional[str] = None,
    status: str = "CLOSED"
):
    """
    Returns a paginated list of trades.
    """
    query = db.query(Order).filter(Order.status == status)
    
    if symbol:
        query = query.filter(Order.symbol == symbol)
    if side:
        query = query.filter(Order.side == side.upper())
        
    total = query.count()
    trades = query.order_by(desc(Order.created_at)).offset((page - 1) * per_page).limit(per_page).all()
    
    # Map to frontend-friendly structure
    formatted_trades = []
    for t in trades:
        formatted_trades.append({
            "id": t.id,
            "symbol": t.symbol,
            "side": t.side,
            "entry_price": t.average_filled_price,
            "exit_price": t.meta_data.get("exit_price", t.average_filled_price), # Fallback if not closed
            "pnl_usd": t.pnl_usd,
            "created_at": t.created_at,
            "status": t.status,
            "meta_data": t.meta_data
        })
    
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "trades": formatted_trades
    }

@router.get("/stats")
async def get_trade_stats(
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """
    Returns performance statistics (Sharpe, Max Drawdown, etc).
    """
    closed_orders = db.query(Order).filter(Order.status == "CLOSED").all()
    if not closed_orders:
        return {"win_rate": 0, "profit_factor": 0, "total_pnl": 0}

    # Basic stats
    wins = [o for o in closed_orders if (o.pnl_usd or 0.0) > 0]
    losses = [o for o in closed_orders if (o.pnl_usd or 0.0) <= 0]
    
    total_pnl = sum([o.pnl_usd or 0.0 for o in closed_orders])
    gross_profit = sum([o.pnl_usd or 0.0 for o in wins])
    gross_loss = abs(sum([o.pnl_usd or 0.0 for o in losses]))
    
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else None

    return {
        "total_trades": len(closed_orders),
        "win_rate": round(len(wins) / len(closed_orders) * 100, 2),
        "total_pnl": round(total_pnl, 2),
        "profit_factor": profit_factor,
        "avg_trade": round(total_pnl / len(closed_orders), 2)
    }

@router.get("/{trade_id}")
async def get_trade_detail(
    trade_id: int,
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """
    Returns detailed info for a single trade, including AI reasoning.
    """
    trade = db.query(Order).filter(Order.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
        
    return trade
