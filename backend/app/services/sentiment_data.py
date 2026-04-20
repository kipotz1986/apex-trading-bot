"""
Market Sentiment Data Service.

Mengambil indikator psikologi pasar dari berbagai sumber:
1. Fear & Greed Index (alternative.me)
2. Funding Rate (Exchange)
3. Open Interest (Exchange)

Usage:
    sentiment = SentimentDataService(exchange_service)
    score = await sentiment.get_composite_sentiment("BTC/USDT")
"""

import httpx
from datetime import datetime
from typing import Dict, Any, Optional
from app.services.exchange import ExchangeService
from app.core.logging import get_logger
from app.schemas.market_data import NormalizedSentiment

logger = get_logger(__name__)

class SentimentDataService:
    """Service untuk agregasi sentimen pasar."""

    def __init__(self, exchange: ExchangeService):
        self.exchange = exchange
        self.fear_greed_url = "https://api.alternative.me/fng/"
        self.timeout = 10.0

    async def get_fear_greed_index(self) -> Dict[str, Any]:
        """Ambil Fear & Greed Index terbaru (0-100)."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.fear_greed_url)
                if response.status_code == 200:
                    data = response.json()
                    fng = data.get("data", [{}])[0]
                    logger.info("fear_greed_fetched", value=fng.get("value"), classification=fng.get("value_classification"))
                    return {
                        "value": int(fng.get("value", 50)),
                        "classification": fng.get("value_classification", "Neutral")
                    }
                return {"value": 50, "classification": "Neutral"}
        except Exception as e:
            logger.error("fear_greed_fetch_failed", error=str(e))
            return {"value": 50, "classification": "Neutral"}

    async def get_exchange_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Ambil Funding Rate dan Open Interest dari exchange."""
        try:
            # Funding Rate
            # Catatan: Tidak semua exchange mendukung fetch_funding_rate di CCXT standar
            # Untuk futures/swap biasanya ada.
            funding_rate = 0.0
            try:
                # CCXT unified method
                fr_data = await self.exchange.exchange.fetch_funding_rate(symbol)
                funding_rate = fr_data.get("fundingRate", 0.0)
            except Exception:
                # Fallback to fetch_tickers if funding rate is included there for some exchanges
                pass

            # Open Interest
            open_interest = 0.0
            try:
                oi_data = await self.exchange.exchange.fetch_open_interest(symbol)
                open_interest = oi_data.get("openInterestAmount", 0.0)
            except Exception:
                pass

            logger.info("exchange_sentiment_fetched", symbol=symbol, funding_rate=funding_rate)
            return {
                "funding_rate": funding_rate,
                "open_interest": open_interest
            }
        except Exception as e:
            logger.error("exchange_sentiment_error", symbol=symbol, error=str(e))
            return {"funding_rate": 0.0, "open_interest": 0.0}

    async def get_composite_sentiment(self, symbol: str) -> NormalizedSentiment:
        """Hitung skor sentimen gabungan dari -100 ke 100."""
        fng = await self.get_fear_greed_index()
        exc = await self.get_exchange_sentiment(symbol)
        
        # 1. Fear & Greed Score: (value - 50) * 2 -> Range -100 to 100
        # 50 is neutral, 0 is extreme fear (-100), 100 is extreme greed (100)
        fng_score = (fng["value"] - 50) * 2
        
        # 2. Funding Rate Score: Biasa berkisar -0.1% s/d 0.1%
        # Positif Tinggi (> 0.03%) = Greed (Overleveraged Longs)
        # Negatif Tinggi (< -0.03%) = Fear (Overleveraged Shorts)
        fr_score = exc["funding_rate"] * 10000 / 3 # Scaling approx
        fr_score = max(min(fr_score, 100), -100)
        
        # Composite: 70% F&G, 30% Exchange Sentiment (Bisa diadjust)
        composite_score = (fng_score * 0.7) + (fr_score * 0.3)
        
        score_round = round(composite_score, 2)
        
        # Simple classification based on score
        classification_str = "Neutral"
        if score_round >= 50:
            classification_str = "Extreme Greed"
        elif score_round >= 10:
            classification_str = "Greed"
        elif score_round <= -50:
            classification_str = "Extreme Fear"
        elif score_round <= -10:
            classification_str = "Fear"
            
        result = NormalizedSentiment(
            source="composite",
            score=score_round,
            classification=classification_str,
            timestamp=datetime.now()
        )
        
        logger.info("composite_sentiment_calculated", symbol=symbol, score=result.score)
        return result
