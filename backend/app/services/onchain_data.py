"""
On-Chain Data Service.

Mengambil data dari blockchain via API pihak ketiga (WhaleAlert, Glassnode, CryptoQuant).
Digunakan untuk analisa fundamental dan deteksi pergerakan uang besar (whale).

Usage:
    onchain = OnChainDataService()
    whales = await onchain.get_whale_movements()
    flows = await onchain.get_exchange_flows("BTC")
"""

import httpx
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class OnChainDataService:
    """Service untuk mengambil data metrik blockchain."""

    def __init__(self):
        self.whale_key = settings.WHALE_ALERT_API_KEY
        self.glassnode_key = settings.GLASSNODE_API_KEY
        self.cryptoquant_key = settings.CRYPTOQUANT_API_KEY
        self.timeout = 10.0

    async def get_whale_movements(self, min_value_usd: int = 500000) -> List[Dict[str, Any]]:
        """
        Ambil transaksi besar (whale) terbaru.
        
        Args:
            min_value_usd: Batas minimal nilai transaksi yang dianggap whale.
        """
        if not self.whale_key:
            logger.warning("whale_alert_api_key_missing")
            return []

        url = "https://api.whale-alert.io/v1/transactions"
        params = {
            "api_key": self.whale_key,
            "min_value": min_value_usd,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    transactions = data.get("transactions", [])
                    logger.info("whale_movements_fetched", count=len(transactions))
                    return transactions
                else:
                    logger.error("whale_alert_api_error", status=response.status_code)
                    return []
        except Exception as e:
            logger.error("whale_alert_fetch_failed", error=str(e))
            return []

    async def get_exchange_flows(self, symbol: str = "BTC") -> Dict[str, Any]:
        """
        Ambil aliran dana bursa (Inflow vs Outflow).
        Menggunakan Glassnode sebagai primary, CryptoQuant sebagai fallback.
        """
        result = {"inflow": 0.0, "outflow": 0.0, "net_flow": 0.0, "provider": None}

        # 1. Try Glassnode
        if self.glassnode_key:
            try:
                # Contoh endpoint Glassnode untuk inflow (sangat simplified)
                # Di produksi, kita akan butuh list endpoint yang benar sesuai dokumentasi mereka
                url = f"https://api.glassnode.com/v1/metrics/exchange/net_flow_sum"
                params = {"api_key": self.glassnode_key, "a": symbol.lower(), "i": "24h"}
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        # Glassnode return list of objects [ {t: timestamp, v: value} ]
                        if data and len(data) > 0:
                            net_flow = data[-1].get("v", 0.0)
                            result.update({
                                "net_flow": net_flow,
                                "provider": "glassnode"
                            })
                            logger.info("exchange_flows_fetched", symbol=symbol, provider="glassnode")
                            return result
            except Exception as e:
                logger.warning("glassnode_fetch_failed", error=str(e))

        # 2. Fallback to CryptoQuant (Jika Glassnode gagal atau key tidak ada)
        if self.cryptoquant_key:
            # Implementasi fallback ke CryptoQuant di sini jika perlu
            pass

        return result

    async def get_summary(self, symbol: str = "BTC") -> Dict[str, Any]:
        """Agregasi data on-chain untuk memberikan skor sentimen fundamental."""
        flows = await self.get_exchange_flows(symbol)
        whales = await self.get_whale_movements()
        
        # Logika scoring sederhana:
        # Net flow positif (banyak masuk ke exchange) = Bearish
        # Banyak whale transfer besar ke exchange = Bearish
        # Banyak whale transfer keluar dari exchange = Bullish
        
        sentiment_score = 0  # -100 (Bearish) to 100 (Bullish)
        
        if flows["net_flow"] > 0:
            sentiment_score -= 20
        elif flows["net_flow"] < 0:
            sentiment_score += 20
            
        # Analisis whale (sementara hanya count)
        whale_count = len(whales)
        if whale_count > 10:
            sentiment_score -= 10 # High activity can be volatile
            
        return {
            "symbol": symbol,
            "sentiment_score": sentiment_score,
            "flows": flows,
            "whale_count": whale_count,
            "timestamp": datetime.now().isoformat()
        }
