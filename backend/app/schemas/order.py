"""
Order Schema.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class OrderResponse(BaseModel):
    """Hasil dari eksekusi order."""
    id: int
    symbol: str
    side: str
    order_type: str
    status: str
    exchange_order_id: Optional[str] = None
    average_filled_price: Optional[float] = None
    filled_amount: float
    pnl_usd: float
    created_at: datetime

    class Config:
        from_attributes = True
