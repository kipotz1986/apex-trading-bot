"""
Market Data Service.

Mengambil dan mengelola data harga historis dan real-time.

Usage:
    from app.services.market_data import MarketDataService
    market = MarketDataService(exchange_service)
    candles = await market.get_candles("BTC/USDT", "1h", limit=200)
"""

from datetime import datetime
from typing import Optional
from app.services.exchange import ExchangeService
from app.core.logging import get_logger

logger = get_logger(__name__)

# Timeframe yang didukung dan jumlah candle default
SUPPORTED_TIMEFRAMES = {
    "15m": {"label": "15 Menit", "candles": 200},
    "1h": {"label": "1 Jam", "candles": 200},
    "4h": {"label": "4 Jam", "candles": 200},
    "1d": {"label": "1 Hari", "candles": 365},
}


class MarketDataService:
    """Service untuk mengambil data pasar."""

    def __init__(self, exchange: ExchangeService):
        self.exchange = exchange

    async def get_candles(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 200,
        since: Optional[datetime] = None,
    ) -> list[dict]:
        """
        Ambil data candlestick/OHLCV.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            timeframe: Periode candle ("15m", "1h", "4h", "1d")
            limit: Jumlah candle terakhir yang diambil
            since: Ambil data sejak tanggal tertentu (opsional)

        Returns:
            List of dict, masing-masing berisi:
            {
                "timestamp": datetime,
                "open": float,
                "high": float,
                "low": float,
                "close": float,
                "volume": float,
            }
        """
        if timeframe not in SUPPORTED_TIMEFRAMES:
            raise ValueError(
                f"Timeframe '{timeframe}' tidak didukung. "
                f"Gunakan: {list(SUPPORTED_TIMEFRAMES.keys())}"
            )

        try:
            since_ms = int(since.timestamp() * 1000) if since else None
            # Pastikan menggunakan objek exchange dari ExchangeService (ccxt)
            raw_data = await self.exchange.exchange.fetch_ohlcv(
                symbol, timeframe, since=since_ms, limit=limit
            )

            candles = []
            for candle in raw_data:
                candles.append({
                    "timestamp": datetime.fromtimestamp(candle[0] / 1000),
                    "open": candle[1],
                    "high": candle[2],
                    "low": candle[3],
                    "close": candle[4],
                    "volume": candle[5],
                })

            logger.info("candles_fetched",
                symbol=symbol,
                timeframe=timeframe,
                count=len(candles)
            )
            return candles

        except Exception as e:
            logger.error("candle_fetch_error",
                symbol=symbol, timeframe=timeframe, error=str(e)
            )
            raise

    async def get_multi_timeframe_candles(
        self,
        symbol: str,
        timeframes: list[str] = None,
    ) -> dict[str, list[dict]]:
        """
        Ambil candle dari beberapa timeframe sekaligus.
        Digunakan oleh Technical Analyst Agent untuk analisis multi-TF.

        Returns:
            Dict dengan key = timeframe, value = list of candles
            {
                "15m": [...candles...],
                "1h": [...candles...],
                "4h": [...candles...],
                "1d": [...candles...],
            }
        """
        if timeframes is None:
            timeframes = list(SUPPORTED_TIMEFRAMES.keys())

        result = {}
        for tf in timeframes:
            limit = SUPPORTED_TIMEFRAMES[tf]["candles"]
            result[tf] = await self.get_candles(symbol, tf, limit)

        return result
