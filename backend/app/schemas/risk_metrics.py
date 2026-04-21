"""
Risk Metrics Schemas.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class RiskMetrics(BaseModel):
    """Metrik risiko untuk dashboard."""
    system_status: str
    current_equity: float
    equity_peak: float
    drawdown_pct: float
    daily_pnl_pct: float
    weekly_pnl_pct: float
    consecutive_losses: int
    is_paused: bool
    paused_until: Optional[datetime] = None

class SystemStatusUpdate(BaseModel):
    """Update status sistem (e.g. manual resume)."""
    new_status: str # NORMAL | REQUIRES_REVIEW | EMERGENCY_STOP
