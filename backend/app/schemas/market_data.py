"""
Market Data Schemas.

Skema Pydantic standar untuk menormalisasi data dari berbagai sumber
ke format internal yang konsisten sebelum dikonsumsi oleh agent.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class NormalizedCandle(BaseModel):
    """Data OHLCV standar."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

class NormalizedTicker(BaseModel):
    """Data harga live standar."""
    symbol: str
    price: float
    change_24h: Optional[float] = None
    volume_24h: Optional[float] = None

class NormalizedSentiment(BaseModel):
    """Data sentimen agregat."""
    source: str = Field(description="Sumber sentimen, misal: 'composite', 'fear_and_greed'")
    score: float = Field(description="Skor sentimen standar: -100 (Bearish/Fear) s/d 100 (Bullish/Greed)")
    classification: str = Field(description="Label sentimen, misal: 'Greed', 'Fear', 'Neutral'")
    timestamp: datetime

class NormalizedNews(BaseModel):
    """Data berita standar."""
    title: str
    source: str
    timestamp: datetime
    url: Optional[str] = None
    importance: str = Field(description="low, medium, high")
    currencies: List[str] = Field(default_factory=list)
    sentiment_score: float = Field(default=0.0, description="Skor sentimen berita: -1.0 s/d 1.0")
