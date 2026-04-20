"""
Crypto News Feed Service.

Mengambil berita terbaru dari CryptoPanic API dan sumber lainnya.
Digunakan oleh Fundamental Analyst Agent untuk memahami sentiment berita.

Usage:
    news_service = NewsFeedService()
    news = await news_service.get_latest_news(currencies=["BTC", "ETH"])
"""

import httpx
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class NewsFeedService:
    """Service untuk agregasi berita kripto."""

    def __init__(self):
        self.api_key = settings.CRYPTOPANIC_API_KEY
        self.base_url = "https://cryptopanic.com/api/v1/posts/"
        self.timeout = 10.0

    async def get_latest_news(
        self, 
        currencies: Optional[List[str]] = None, 
        filter: str = "hot",
        kind: str = "news"
    ) -> List[Dict[str, Any]]:
        """
        Ambil berita terbaru dari CryptoPanic.
        
        Args:
            currencies: List simbol koin (e.g., ["BTC", "ETH"])
            filter: Tipe filter ("all", "hot", "rising", "bullish", "bearish")
            kind: Jenis konten ("news" atau "media")
        """
        if not self.api_key:
            logger.warning("cryptopanic_api_key_missing")
            return []

        params = {
            "auth_token": self.api_key,
            "filter": filter,
            "kind": kind,
            "public": "true"
        }

        if currencies:
            params["currencies"] = ",".join(currencies)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    
                    normalized_news = []
                    for item in results:
                        normalized_news.append({
                            "title": item.get("title"),
                            "source": item.get("domain"),
                            "url": item.get("url"),
                            "timestamp": item.get("created_at"),
                            "importance": self._calculate_importance(item),
                            "currencies": [c.get("code") for c in item.get("currencies", [])],
                            "votes": item.get("votes")
                        })
                    
                    logger.info("news_fetched", count=len(normalized_news))
                    return normalized_news
                else:
                    logger.error("cryptopanic_api_error", status=response.status_code)
                    return []
        except Exception as e:
            logger.error("news_fetch_failed", error=str(e))
            return []

    def _calculate_importance(self, item: Dict[str, Any]) -> str:
        """Menentukan tingkat kepentingan berita berdasarkan jumlah vote."""
        votes = item.get("votes", {})
        total_votes = votes.get("positive", 0) + votes.get("negative", 0) + votes.get("important", 0)
        
        if votes.get("important", 0) > 10 or total_votes > 100:
            return "high"
        elif total_votes > 50:
            return "medium"
        else:
            return "low"
