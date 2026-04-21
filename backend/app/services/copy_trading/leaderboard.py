"""
Leaderboard Service.

Interface untuk mengambil data top traders dari exchange.
"""

import asyncio
import httpx
from typing import List, Dict, Any
from app.schemas.copy_trading import TraderStats, LeaderboardResponse
from app.core.logging import get_logger

logger = get_logger(__name__)

class BaseLeaderboardService:
    """Base class untuk leaderboard services."""
    def __init__(self, exchange_name: str):
        self.exchange_name = exchange_name

    async def fetch(self) -> List[TraderStats]:
        raise NotImplementedError

class BybitLeaderboardService(BaseLeaderboardService):
    """Fetcher untuk Bybit Copy Trading leaderboard."""

    def __init__(self):
        super().__init__("bybit")
        self.url = "https://api2.bybit.com/fapi/becc/public/get-leaderboard" # Mock/Discovery URL

    async def fetch(self) -> List[TraderStats]:
        """
        Ambil data trader dari Bybit.
        
        Karena lingkungan ini tidak memiliki akses internet langsung untuk scraping, 
        kita akan menggunakan mock data yang realistis untuk pengembangan, 
        namun dengan struktur yang siap untuk dihubungkan ke httpx.
        """
        logger.info("fetching_bybit_leaderboard")
        
        # Mocking HTTP call
        # In actual prod, this would be: 
        # async with httpx.AsyncClient() as client:
        #     resp = await client.get(self.url, params={"limit": 50})
        #     data = resp.json()
        
        await asyncio.sleep(0.5) # Simulate IO
        
        mock_data = [
            {
                "trader_id": "T001",
                "username": "DiamondHands",
                "roi_pct": 150.5,
                "win_rate_pct": 72.0,
                "pnl_usd": 50000.0,
                "max_drawdown_pct": 12.5,
                "track_record_days": 120,
                "followers_count": 500
            },
            {
                "trader_id": "T002",
                "username": "TrendFollower",
                "roi_pct": 85.0,
                "win_rate_pct": 68.5,
                "pnl_usd": 12000.0,
                "max_drawdown_pct": 8.0,
                "track_record_days": 45,
                "followers_count": 120
            },
            {
                "trader_id": "T003",
                "username": "HighLevGambler",
                "roi_pct": 1200.0,
                "win_rate_pct": 55.0,
                "pnl_usd": 80000.0,
                "max_drawdown_pct": 65.0,
                "track_record_days": 15,
                "followers_count": 2000
            },
            {
                "trader_id": "T004",
                "username": "StablePro",
                "roi_pct": 45.0,
                "win_rate_pct": 82.0,
                "pnl_usd": 5000.0,
                "max_drawdown_pct": 3.5,
                "track_record_days": 365,
                "followers_count": 50
            }
        ]
        
        traders = [TraderStats(**t) for t in mock_data]
        logger.info("leaderboard_fetched", count=len(traders))
        return traders
