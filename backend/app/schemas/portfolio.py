"""
Portfolio and Risk Schemas.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class Position(BaseModel):
    """Representasi posisi trading aktif."""
    symbol: str
    side: str  # "LONG" | "SHORT"
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    leverage: int = 1

class PortfolioState(BaseModel):
    """Status portfolio saat ini untuk evaluasi risiko."""
    total_balance: float
    total_equity: float
    available_margin: float
    open_positions: List[Position] = Field(default_factory=list)
    daily_pnl_pct: float
    weekly_pnl_pct: float
    max_drawdown_pct: float

class RiskDecision(BaseModel):
    """Output dari Risk Manager Agent."""
    decision: str = Field(..., description="APPROVE | REJECT | REDUCE_SIZE")
    max_position_size_usd: float
    max_leverage: int
    reasoning: str
    risk_metrics: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
