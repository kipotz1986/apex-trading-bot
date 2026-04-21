"""
Trade Decision Schema.
Mendefinisikan format keputusan final dari Master Orchestrator.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.schemas.agent_signal import AgentSignal

class TradeDecision(BaseModel):
    """Keputusan final trading hasil konsensus multi-agent."""
    symbol: str = Field(..., description="Trading pair (e.g., BTC/USDT)")
    action: str = Field(..., description="EXECUTE_LONG | EXECUTE_SHORT | CLOSE | HOLD")
    confidence: float = Field(..., description="Skor kepercayaan final (0.0 - 1.0)")
    consensus_score: float = Field(..., description="Skor numerik hasil weighted voting")
    
    # Parameter eksekusi
    position_size_usd: float = Field(default=0.0)
    leverage: int = Field(default=1)
    stop_loss: Optional[float] = None
    take_profit: List[float] = Field(default_factory=list)
    
    # Rationale & Traceability
    reasoning: str = Field(..., description="Penjelasan logis di balik keputusan final")
    agent_signals: Dict[str, AgentSignal] = Field(..., description="Snapshot sinyal dari setiap agen analis")
    
    # Kondisi pasar saat keputusan dibuat
    market_regime: str = Field(default="unknown")
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "BTC/USDT",
                "action": "EXECUTE_LONG",
                "confidence": 0.85,
                "consensus_score": 0.82,
                "position_size_usd": 500.0,
                "leverage": 3,
                "stop_loss": 61500.0,
                "take_profit": [65000.0, 67000.0],
                "reasoning": "Konsensus kuat antara Technical dan Sentiment. Risk Manager menyetujui size.",
                "market_regime": "trending_up",
                "timestamp": "2024-03-20T10:05:00"
            }
        }
