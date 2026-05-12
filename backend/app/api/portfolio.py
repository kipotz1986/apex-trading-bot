"""
Portfolio and PnL Data Router.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, time, timedelta
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
    Calculates real-time PnL from closed and open orders.
    """
    risk_state = db.query(RiskState).first()
    
    # If balance is 0, try to sync it once from the exchange
    if risk_state and risk_state.current_equity <= 0:
        try:
            from app.core.factory import ServiceFactory
            factory = ServiceFactory._instance
            if factory and factory.exchange:
                # Reuse the logic from bot_runner (simplified here)
                balance = await factory.exchange.get_balance()
                total_equity = 0.0
                if 'info' in balance and 'result' in balance['info'] and 'list' in balance['info']['result']:
                    total_equity = float(balance['info']['result']['list'][0].get('totalEquity', 0.0))
                
                if total_equity <= 0 and 'total' in balance:
                    total_equity = balance['total'].get('USDT', 0.0) + balance['total'].get('USDC', 0.0)
                
                if total_equity > 0:
                    risk_state.current_equity = total_equity
                    db.commit()
                    logger.info("portfolio_summary_balance_synced", equity=total_equity)
        except Exception as e:
            logger.warning("portfolio_summary_sync_failed", error=str(e))

    if not risk_state:
        return {
            "balance": 0.0,
            "equity": 0.0,
            "unrealized_pnl": 0.0,
            "daily_pnl": 0.0,
            "total_trades": 0,
            "win_rate": 0.0
        }

    # 1. Unrealized PnL from open positions
    open_positions = db.query(Order).filter(Order.status.in_(["OPEN", "FILLED"])).all()
    unrealized_pnl = sum([p.pnl_usd or 0.0 for p in open_positions])

    # 2. Daily PnL (Closed trades today + Unrealized movement)
    today_start = datetime.combine(datetime.now().date(), time.min)
    daily_closed_pnl = db.query(func.sum(Order.pnl_usd)).filter(
        Order.status == "CLOSED", 
        Order.updated_at >= today_start
    ).scalar() or 0.0
    
    # 3. Overall Win Rate
    closed_orders_query = db.query(Order).filter(Order.status == "CLOSED")
    total_trades = closed_orders_query.count()
    winning_trades = closed_orders_query.filter(Order.pnl_usd > 0).count()
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
    
    # 4. Total PnL (All closed trades)
    total_pnl = db.query(func.sum(Order.pnl_usd)).filter(Order.status == "CLOSED").scalar() or 0.0

    return {
        "balance": risk_state.current_equity - unrealized_pnl, # Simplified: Balance = Equity - Unrealized
        "equity": risk_state.current_equity,
        "unrealized_pnl": round(unrealized_pnl, 2),
        "daily_pnl": round(daily_closed_pnl + unrealized_pnl, 2),
        "total_pnl": round(total_pnl, 2),
        "win_rate": round(win_rate, 2),
        "total_trades": total_trades,
        "system_status": risk_state.system_status,
        "mode": "live" if risk_state.is_live_enabled else "paper"
    }

@router.get("/equity-history")
async def get_equity_history(
    hours: int = 24,
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """
    Returns time-series data for the equity curve chart.
    hours=0 means ALL history. Otherwise filters to the last N hours.
    Snapshot density: saved every 60s, so limit = hours * 60 capped at 2000.
    """
    query = db.query(RiskSnapshot)

    if hours > 0:
        since = datetime.utcnow() - timedelta(hours=hours)
        query = query.filter(RiskSnapshot.timestamp >= since)

    # Snapshots saved every ~60s. Cap to avoid huge payloads.
    limit = min(hours * 60, 2000) if hours > 0 else 2000

    snapshots = query.order_by(RiskSnapshot.timestamp.desc()).limit(limit).all()
    snapshots.reverse()

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
    Returns all currently open positions with real-time PnL calculation.
    """
    positions = db.query(Order).filter(Order.status.in_(["OPEN", "FILLED"])).all()
    
    return [
        {
            "id": p.id,
            "symbol": p.symbol,
            "side": p.side,
            "size": p.requested_amount,
            "entry": p.average_filled_price or 0.0,
            "current": p.average_filled_price or 0.0, # Will be updated by frontend/bot later
            "leverage": p.leverage,
            "pnl": p.pnl_usd or 0.0,
            "pnl_percent": None,  # Updated by WebSocket market data stream (current price not stored)
            "status": "profit" if (p.pnl_usd or 0.0) >= 0 else "loss"
        }
        for p in positions
    ]

@router.get("/klines")
async def get_klines(
    symbol: str = "BTC/USDT",
    timeframe: str = "1m",
    limit: int = 200,
    current_user: str = Depends(deps.get_current_user)
):
    """
    Returns historical OHLCV candles for the candlestick chart.
    symbol: BTC/USDT | ETH/USDT | SOL/USDT
    timeframe: 1m | 5m | 15m | 1h | 4h
    """
    SYMBOL_MAP = {
        "BTC/USDT": "BTC/USDT:USDT",
        "ETH/USDT": "ETH/USDT:USDT",
        "SOL/USDT": "SOL/USDT:USDT",
    }
    ccxt_symbol = SYMBOL_MAP.get(symbol, symbol)
    try:
        from app.core.factory import ServiceFactory
        factory = ServiceFactory._instance
        if not factory or not factory.exchange:
            return []
        candles = await factory.exchange.fetch_ohlcv(ccxt_symbol, timeframe, limit=limit)
        return [
            {
                "time": int(c[0]) // 1000,
                "open": c[1],
                "high": c[2],
                "low": c[3],
                "close": c[4],
                "volume": c[5],
            }
            for c in candles
        ]
    except Exception as e:
        logger.error("klines_fetch_error", symbol=symbol, timeframe=timeframe, error=str(e))
        return []


@router.post("/close/{order_id}")
async def close_position_manually(
    order_id: int,
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """
    Manually closes an open position.
    """
    order = db.query(Order).filter(Order.id == order_id, Order.status.in_(["OPEN", "FILLED"])).first()
    if not order:
        raise HTTPException(status_code=404, detail="Position not found")

    try:
        from app.core.factory import ServiceFactory
        orchestrator = ServiceFactory.get_orchestrator(db)
        
        success = await orchestrator.executor.close_position(
            symbol=order.symbol,
            side=order.side,
            amount=order.requested_amount,
            order_id=order_id
        )
        
        if success:
            logger.info("position_closed_manually", order_id=order_id, user=current_user)
            return {"message": "Position closing initiated"}
        else:
            raise HTTPException(status_code=500, detail="Failed to close position on exchange")
            
    except Exception as e:
        logger.error("manual_close_failed", order_id=order_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
