from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api import deps
from app.services.backtesting import BacktestEngine
from app.services.candle_storage import CandleStorageService
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

class BacktestRequest(BaseModel):
    symbol: str
    timeframe: str = "1h"
    start_date: datetime
    end_date: datetime
    initial_balance: float = 10000.0

@router.post("/run")
async def run_backtest(
    request: BacktestRequest,
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """
    Menjalankan pengujian strategi pada data historis.
    """
    candle_service = CandleStorageService(db)
    
    # 1. Ambil data historis
    # (Note: In a real app, this might fetch from exchange if not in DB)
    candles = candle_service.get_candles(
        symbol=request.symbol,
        timeframe=request.timeframe,
        start_time=request.start_date,
        limit=2000 # limit to 2000 candles for simulation speed
    )
    
    if not candles or len(candles) < 50:
        raise HTTPException(
            status_code=400, 
            detail=f"Not enough historical data for {request.symbol}. Found {len(candles)} candles."
        )

    # Convert SQLAlchemy objects to Dicts for engine
    candle_data = []
    for c in candles:
        candle_data.append({
            "timestamp": c.timestamp,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume
        })

    # 2. Setup Engine
    # (Simplified: We use a lightweight version of orchestrator or mock it)
    # For now, let's use the actual engine if we can.
    # Note: Orchestrator initialization is complex, so we might need a Factory.
    
    # Placeholder for a simpler backtest until Orchestrator Factory is ready
    engine = BacktestEngine(db, None) # None for orchestrator for now
    
    # Overriding the run method logic internally or using a specific backtest strategy
    results = await engine.run(
        symbol=request.symbol,
        historical_candles=candle_data,
        initial_balance=request.initial_balance
    )
    
    return results
