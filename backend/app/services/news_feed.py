"""
Crypto News Feed Service.

Mengambil berita terbaru dari CryptoPanic API dan sumber lainnya.
Digunakan oleh Fundamental Analyst Agent untuk memahami sentiment berita.

Usage:
    news_service = NewsFeedService()
    news = await news_service.get_latest_news(currencies=["BTC", "ETH"])
"""

import httpx
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.market_data import NormalizedNews

logger = get_logger(__name__)

class NewsFeedService:
    """Service untuk agregasi berita kripto."""

    def __init__(self):
        self.base_url = "https://min-api.cryptocompare.com/data/v2/news/"
        self.timeout = 10.0

    async def get_latest_news(
        self, 
        currencies: Optional[List[str]] = None, 
        filter: str = "hot",
        kind: str = "news"
    ) -> List[NormalizedNews]:
        """
        Ambil berita terbaru dari CryptoCompare (100% Free Public API).
        
        Args:
            currencies: List simbol koin (e.g., ["BTC", "ETH"])
            filter: (Hanya untuk kompatibilitas fungsi lama, tidak terpakai di CryptoCompare)
            kind: (Hanya untuk kompatibilitas fungsi lama, tidak terpakai)
        """
        params = {"lang": "EN"}

        if currencies:
            params["categories"] = ",".join(currencies)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("Data", [])
                    
                    normalized_news = []
                    for item in results:
                        timestamp = item.get("published_on")
                        dt_obj = datetime.fromtimestamp(timestamp, tz=timezone.utc) if timestamp else datetime.now(timezone.utc)

                        normalized_news.append(NormalizedNews(
                            title=item.get("title", ""),
                            source=item.get("source_info", {}).get("name", "CryptoCompare"),
                            timestamp=dt_obj,
                            url=item.get("url"),
                            importance=self._calculate_importance(item),
                            currencies=item.get("categories", "").split("|")
                        ))
                    
                    logger.info("news_fetched", count=len(normalized_news))
                    return normalized_news
                else:
                    logger.error("cryptocompare_api_error", status=response.status_code)
                    return []
        except Exception as e:
            logger.error("news_fetch_failed", error=str(e))
            return []

    def _calculate_importance(self, item: Dict[str, Any]) -> str:
        """Menentukan tingkat kepentingan berita berdasarkan upvotes."""
        upvotes = int(item.get("upvotes", 0))
        
        if upvotes > 20:
            return "high"
        elif upvotes > 5:
            return "medium"
        else:
            return "low"
