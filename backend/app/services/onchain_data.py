"""
On-Chain Data Service (Free Providers).

Mengambil data blockchain dan market metrics menggunakan API gratis:
1. CoinGecko — Market metrics, trending, global data
2. Blockchain.com — BTC on-chain stats (tanpa API key)
3. Etherscan — ETH whale tracking, large transfers (free tier)

Usage:
    onchain = OnChainDataService()
    btc_stats = await onchain.get_btc_onchain_stats()
    eth_whales = await onchain.get_eth_large_transfers()
    summary = await onchain.get_summary("BTC")
"""

import httpx
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.market_data import NormalizedSentiment

logger = get_logger(__name__)


class OnChainDataService:
    """Service untuk mengambil data metrik blockchain dari provider gratis."""

    def __init__(self):
        self.coingecko_key = settings.COINGECKO_API_KEY
        self.etherscan_key = settings.ETHERSCAN_API_KEY
        self.timeout = 10.0

        # Base URLs
        self.coingecko_url = "https://api.coingecko.com/api/v3"
        self.blockchain_url = "https://api.blockchain.info"
        self.etherscan_url = "https://api.etherscan.io/api"

    # ─── CoinGecko: Market Metrics ─────────────────────────────────────

    async def get_global_market(self) -> Dict[str, Any]:
        """
        Ambil global market metrics dari CoinGecko.
        Contoh: total market cap, volume 24h, BTC dominance.
        """
        url = f"{self.coingecko_url}/global"
        headers = {}
        if self.coingecko_key:
            headers["x-cg-demo-api-key"] = self.coingecko_key

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json().get("data", {})
                    result = {
                        "total_market_cap_usd": data.get("total_market_cap", {}).get("usd", 0),
                        "total_volume_24h_usd": data.get("total_volume", {}).get("usd", 0),
                        "btc_dominance": data.get("market_cap_percentage", {}).get("btc", 0),
                        "active_cryptocurrencies": data.get("active_cryptocurrencies", 0),
                        "market_cap_change_24h_pct": data.get("market_cap_change_percentage_24h_usd", 0),
                    }
                    logger.info("coingecko_global_fetched", btc_dominance=result["btc_dominance"])
                    return result
                else:
                    logger.error("coingecko_global_error", status=response.status_code)
                    return {}
        except Exception as e:
            logger.error("coingecko_global_failed", error=str(e))
            return {}

    async def get_trending_coins(self) -> List[Dict[str, Any]]:
        """Ambil daftar coin yang sedang trending dari CoinGecko."""
        url = f"{self.coingecko_url}/search/trending"
        headers = {}
        if self.coingecko_key:
            headers["x-cg-demo-api-key"] = self.coingecko_key

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    coins = response.json().get("coins", [])
                    result = []
                    for coin in coins:
                        item = coin.get("item", {})
                        result.append({
                            "name": item.get("name"),
                            "symbol": item.get("symbol"),
                            "market_cap_rank": item.get("market_cap_rank"),
                            "score": item.get("score"),
                        })
                    logger.info("coingecko_trending_fetched", count=len(result))
                    return result
                return []
        except Exception as e:
            logger.error("coingecko_trending_failed", error=str(e))
            return []

    # ─── Blockchain.com: BTC On-Chain Stats ────────────────────────────

    async def get_btc_onchain_stats(self) -> Dict[str, Any]:
        """
        Ambil statistik on-chain BTC dari Blockchain.com (GRATIS, tanpa API key).
        Data: hashrate, mempool size, avg block size, unconfirmed txs.
        """
        result = {
            "hash_rate": 0,
            "mempool_size": 0,
            "avg_block_size": 0,
            "unconfirmed_txs": 0,
            "difficulty": 0,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Blockchain.com menyediakan endpoint stats mentah
                stats_response = await client.get(f"{self.blockchain_url}/stats")
                if stats_response.status_code == 200:
                    data = stats_response.json()
                    result.update({
                        "hash_rate": data.get("hash_rate", 0),
                        "avg_block_size": data.get("blocks_avg", 0),
                        "difficulty": data.get("difficulty", 0),
                        "n_blocks_total": data.get("n_blocks_total", 0),
                        "minutes_between_blocks": data.get("minutes_between_blocks", 0),
                    })

                # Unconfirmed transaction count
                unconf_response = await client.get(f"{self.blockchain_url}/q/unconfirmedcount")
                if unconf_response.status_code == 200:
                    result["unconfirmed_txs"] = int(unconf_response.text.strip())

            logger.info("blockchain_stats_fetched", hash_rate=result["hash_rate"])
            return result

        except Exception as e:
            logger.error("blockchain_stats_failed", error=str(e))
            return result

    # ─── Etherscan: ETH Large Transfers ────────────────────────────────

    async def get_eth_large_transfers(self, min_value_eth: float = 100.0) -> List[Dict[str, Any]]:
        """
        Ambil transfer ETH besar terbaru dari Etherscan (free tier).
        Menggunakan internal transaction list dari block terbaru.

        Args:
            min_value_eth: Minimal jumlah ETH yang dianggap whale transfer.
        """
        if not self.etherscan_key:
            logger.warning("etherscan_api_key_missing")
            return []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Ambil block terbaru
                params = {
                    "module": "proxy",
                    "action": "eth_blockNumber",
                    "apikey": self.etherscan_key,
                }
                block_response = await client.get(self.etherscan_url, params=params)
                if block_response.status_code != 200:
                    return []

                latest_block = block_response.json().get("result", "0x0")

                # Ambil transaksi dari block terbaru
                tx_params = {
                    "module": "proxy",
                    "action": "eth_getBlockByNumber",
                    "tag": latest_block,
                    "boolean": "true",
                    "apikey": self.etherscan_key,
                }
                tx_response = await client.get(self.etherscan_url, params=tx_params)
                if tx_response.status_code != 200:
                    return []

                block_data = tx_response.json().get("result", {})
                transactions = block_data.get("transactions", [])

                # Filter by value (ETH in Wei, 1 ETH = 10^18 Wei)
                min_wei = int(min_value_eth * 10**18)
                large_txs = []
                for tx in transactions:
                    value_hex = tx.get("value", "0x0")
                    value_wei = int(value_hex, 16) if value_hex else 0
                    if value_wei >= min_wei:
                        large_txs.append({
                            "hash": tx.get("hash"),
                            "from": tx.get("from"),
                            "to": tx.get("to"),
                            "value_eth": value_wei / 10**18,
                            "block": tx.get("blockNumber"),
                        })

                logger.info("etherscan_large_transfers_fetched", count=len(large_txs))
                return large_txs

        except Exception as e:
            logger.error("etherscan_fetch_failed", error=str(e))
            return []

    # ─── Etherscan: Gas Tracker ────────────────────────────────────────

    async def get_eth_gas_price(self) -> Dict[str, Any]:
        """Ambil gas price ETH terkini dari Etherscan."""
        if not self.etherscan_key:
            return {"low": 0, "average": 0, "high": 0}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {
                    "module": "gastracker",
                    "action": "gasoracle",
                    "apikey": self.etherscan_key,
                }
                response = await client.get(self.etherscan_url, params=params)
                if response.status_code == 200:
                    data = response.json().get("result", {})
                    return {
                        "low": float(data.get("SafeGasPrice", 0)),
                        "average": float(data.get("ProposeGasPrice", 0)),
                        "high": float(data.get("FastGasPrice", 0)),
                    }
                return {"low": 0, "average": 0, "high": 0}
        except Exception as e:
            logger.error("etherscan_gas_failed", error=str(e))
            return {"low": 0, "average": 0, "high": 0}

    # ─── Aggregated Summary ────────────────────────────────────────────

    async def get_summary(self, symbol: str = "BTC") -> NormalizedSentiment:
        """
        Agregasi data on-chain untuk memberikan skor sentimen fundamental.

        Skor dihitung berdasarkan:
        - BTC dominance trend (dari CoinGecko)
        - Market cap change 24h (dari CoinGecko)
        - BTC unconfirmed tx count (dari Blockchain.com - mempool congestion)
        """
        global_market = await self.get_global_market()
        btc_stats = await self.get_btc_onchain_stats()

        sentiment_score = 0  # -100 (Bearish) to 100 (Bullish)

        # 1. Market cap change 24h
        mc_change = global_market.get("market_cap_change_24h_pct", 0)
        if mc_change > 3:
            sentiment_score += 25
        elif mc_change > 0:
            sentiment_score += 10
        elif mc_change < -3:
            sentiment_score -= 25
        elif mc_change < 0:
            sentiment_score -= 10

        # 2. BTC Dominance > 50% = flight to safety (slightly bearish for alts)
        btc_dom = global_market.get("btc_dominance", 50)
        if btc_dom > 55:
            sentiment_score -= 5  # Capital leaving alts
        elif btc_dom < 40:
            sentiment_score += 5  # Alt season

        # 3. Mempool congestion (many unconfirmed txs = network busy = high demand)
        unconfirmed = btc_stats.get("unconfirmed_txs", 0)
        if unconfirmed > 100000:
            sentiment_score += 10  # Network sangat sibuk
        elif unconfirmed > 50000:
            sentiment_score += 5

        # Classify
        classification = "Neutral"
        if sentiment_score >= 20:
            classification = "Bullish"
        elif sentiment_score <= -20:
            classification = "Bearish"

        return NormalizedSentiment(
            source="onchain_free",
            score=sentiment_score,
            classification=classification,
            timestamp=datetime.now()
        )
