"""
Agent Signal Schema.
Mendefinisikan format standar untuk output dari semua trader agents.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime

class AgentSignal(BaseModel):
    """Output standar dari setiap agent analisis."""
    agent_name: str = Field(..., description="Nama agent yang memberikan sinyal")
    symbol: str = Field(..., description="Trading pair (e.g., BTC/USDT)")
    signal: str = Field(..., description="STRONG_BUY | BUY | NEUTRAL | SELL | STRONG_SELL")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Skor kepercayaan 0.0 sampai 1.0")
    reasoning: str = Field(..., description="Penjelasan di balik sinyal tersebut")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Metadata spesifik per agent (misal: value indikator, levels, dll)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "agent_name": "technical_analyst",
                "symbol": "BTC/USDT",
                "signal": "BUY",
                "confidence": 0.85,
                "reasoning": "RSI di bawah 30 (oversold) dan MACD bullish crossover pada timeframe 1H.",
                "timestamp": "2024-03-20T10:00:00",
                "metadata": {
                    "rsi": 28.5,
                    "macd_cross": True,
                    "key_levels": {"support": 62000, "resistance": 68000}
                }
            }
        }
