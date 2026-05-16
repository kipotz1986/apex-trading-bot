from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api import deps
from app.services.backtesting import BacktestEngine
from app.services.candle_storage import CandleStorageService
from app.core.factory import create_orchestrator
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
    Menjalankan pengujian strategi pada data historis menggunakan orchestrator aktual.
    """
    candle_service = CandleStorageService(db)
    
    # 1. Ambil data historis
    # Mengambil data dari storage lokal yang sudah disinkronisasi
    candles = candle_service.get_candles(
        symbol=request.symbol,
        timeframe=request.timeframe,
        start_time=request.start_date,
        limit=2000 # limit untuk kecepatan simulasi
    )
    
    if not candles or len(candles) < 50:
        raise HTTPException(
            status_code=400, 
            detail=f"Data historis tidak cukup untuk {request.symbol}. Ditemukan {len(candles)} candle."
        )

    # Konversi objek SQLAlchemy ke list dictionary untuk engine
    candle_data = [
        {
            "timestamp": c.timestamp,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume
        }
        for c in candles
    ]

    # 2. Inisialisasi Orchestrator via Factory
    # Ini memastikan strategi yang sama digunakan di live dan backtest.
    orchestrator = await create_orchestrator(db)
    
    # 3. Jalankan Engine dengan Orchestrator asli
    engine = BacktestEngine(db, orchestrator)
    
    results = await engine.run(
        symbol=request.symbol,
        historical_candles=candle_data,
        initial_balance=request.initial_balance
    )
    
    return results
