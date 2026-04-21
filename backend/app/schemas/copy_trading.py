"""
Copy Trading Schemas.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class TraderStats(BaseModel):
    """Schema untuk statistik trader dari leaderboard."""
    trader_id: str
    username: Optional[str] = None
    exchange: str = "bybit"
    roi_pct: float
    win_rate_pct: float
    pnl_usd: float
    max_drawdown_pct: float
    track_record_days: int
    followers_count: int

class LeaderboardResponse(BaseModel):
    """Hasil fetching dari exchange."""
    exchange: str
    timestamp: datetime = Field(default_factory=datetime.now)
    traders: List[TraderStats]

class CopyTradeEventSchema(BaseModel):
    """Sinyal aktivitas trader."""
    trader_id: str
    symbol: str
    side: str  # "BUY" | "SELL"
    event_type: str  # "OPEN" | "CLOSE"
    entry_price: float
    size_usd: float
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
