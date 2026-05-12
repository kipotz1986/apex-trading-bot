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
from app.services.integration_logger import log_integration

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
        # Solana mainnet public RPC (no API key needed)
        self.solana_rpc_url = "https://api.mainnet-beta.solana.com"

    # ─── CoinGecko: Market Metrics ─────────────────────────────────────

    @log_integration(service_type="DATA_FEED", provider_name="COINGECKO", endpoint="global")
    async def get_global_market(self) -> Dict[str, Any]:
        """
        Ambil global market metrics dari CoinGecko.
        Contoh: total market cap, volume 24h, BTC dominance.
        """
        url = f"{self.coingecko_url}/global"
        headers = {}
        if self.coingecko_key:
            headers["x-cg-demo-api-key"] = self.coingecko_key

        from app.services.integration_logger import IntegrationLogger
        IntegrationLogger.record_request(url=url, method="GET", headers=headers)

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

    @log_integration(service_type="DATA_FEED", provider_name="COINGECKO", endpoint="trending")
    async def get_trending_coins(self) -> List[Dict[str, Any]]:
        """Ambil daftar coin yang sedang trending dari CoinGecko."""
        url = f"{self.coingecko_url}/search/trending"
        headers = {}
        if self.coingecko_key:
            headers["x-cg-demo-api-key"] = self.coingecko_key

        from app.services.integration_logger import IntegrationLogger
        IntegrationLogger.record_request(url=url, method="GET", headers=headers)

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

    @log_integration(service_type="DATA_FEED", provider_name="BLOCKCHAIN.COM", endpoint="stats")
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
                url = f"{self.blockchain_url}/stats"
                from app.services.integration_logger import IntegrationLogger
                IntegrationLogger.record_request(url=url, method="GET")
                
                stats_response = await client.get(url)
                if stats_response.status_code == 200:
                    data = stats_response.json()
                    result.update({
                        "hash_rate": data.get("hash_rate", 0),
                        "avg_block_size": data.get("blocks_size", 0),
                        "difficulty": data.get("difficulty", 0),
                        "n_blocks_total": data.get("n_blocks_total", 0),
                        "minutes_between_blocks": data.get("minutes_between_blocks", 0),
                    })

                # Unconfirmed transaction count
                unconf_url = f"{self.blockchain_url}/q/unconfirmedcount"
                unconf_response = await client.get(unconf_url)
                if unconf_response.status_code == 200:
                    result["unconfirmed_txs"] = int(unconf_response.text.strip())

            logger.info("blockchain_stats_fetched", hash_rate=result["hash_rate"])
            return result

        except Exception as e:
            logger.error("blockchain_stats_failed", error=str(e))
            return result

    # ─── Etherscan: ETH Large Transfers ────────────────────────────────

    @log_integration(service_type="DATA_FEED", provider_name="ETHERSCAN", endpoint="large_transfers")
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
                from app.services.integration_logger import IntegrationLogger
                IntegrationLogger.record_request(url=self.etherscan_url, method="GET", body={"min_value_eth": min_value_eth})

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
                # Etherscan can return a string error when key missing/invalid
                if not isinstance(block_data, dict):
                    logger.warning("etherscan_block_invalid_response", body=str(block_data)[:80])
                    return []
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

    @log_integration(service_type="DATA_FEED", provider_name="ETHERSCAN", endpoint="gas_oracle")
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
                from app.services.integration_logger import IntegrationLogger
                IntegrationLogger.record_request(url=self.etherscan_url, method="GET", body=params)
                response = await client.get(self.etherscan_url, params=params)
                if response.status_code == 200:
                    data = response.json().get("result", {})
                    # Etherscan returns a string ("NOTOK", error msg, etc.) when key is missing/invalid
                    if not isinstance(data, dict):
                        logger.warning("etherscan_gas_invalid_response", body=str(data)[:80])
                        return {"low": 0, "average": 0, "high": 0}
                    return {
                        "low": float(data.get("SafeGasPrice", 0)),
                        "average": float(data.get("ProposeGasPrice", 0)),
                        "high": float(data.get("FastGasPrice", 0)),
                    }
                return {"low": 0, "average": 0, "high": 0}
        except Exception as e:
            logger.error("etherscan_gas_failed", error=str(e))
            return {"low": 0, "average": 0, "high": 0}

    # ─── Solana Public RPC: SOL On-Chain Stats ─────────────────────────

    @log_integration(service_type="DATA_FEED", provider_name="SOLANA_RPC", endpoint="getRecentPerformance")
    async def get_sol_onchain_stats(self) -> Dict[str, Any]:
        """
        Ambil statistik on-chain SOL dari Solana mainnet public RPC (free, no key).
        Returns: TPS, slot height, validator count, recent performance samples.
        """
        result = {
            "tps": 0.0,
            "slot_height": 0,
            "epoch": 0,
            "samples": 0,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                from app.services.integration_logger import IntegrationLogger
                IntegrationLogger.record_request(url=self.solana_rpc_url, method="POST", body={"method": "getRecentPerformanceSamples"})

                # 1. Recent performance: returns TPS samples (each ~60s window)
                perf_payload = {
                    "jsonrpc": "2.0", "id": 1,
                    "method": "getRecentPerformanceSamples",
                    "params": [4],  # last 4 samples (~4 minutes)
                }
                perf_resp = await client.post(self.solana_rpc_url, json=perf_payload)
                if perf_resp.status_code == 200:
                    samples = perf_resp.json().get("result", [])
                    if samples:
                        # TPS = sum(num_transactions) / sum(sample_period_secs)
                        total_tx = sum(s.get("numTransactions", 0) for s in samples)
                        total_sec = sum(s.get("samplePeriodSecs", 60) for s in samples)
                        result["tps"] = round(total_tx / total_sec, 2) if total_sec > 0 else 0
                        result["samples"] = len(samples)

                # 2. Current slot (block height equivalent)
                slot_payload = {"jsonrpc": "2.0", "id": 2, "method": "getSlot"}
                slot_resp = await client.post(self.solana_rpc_url, json=slot_payload)
                if slot_resp.status_code == 200:
                    result["slot_height"] = slot_resp.json().get("result", 0)

                # 3. Current epoch info
                epoch_payload = {"jsonrpc": "2.0", "id": 3, "method": "getEpochInfo"}
                epoch_resp = await client.post(self.solana_rpc_url, json=epoch_payload)
                if epoch_resp.status_code == 200:
                    info = epoch_resp.json().get("result", {})
                    result["epoch"] = info.get("epoch", 0)

            logger.info("solana_stats_fetched", tps=result["tps"], slot=result["slot_height"])
            return result
        except Exception as e:
            logger.error("solana_stats_failed", error=str(e))
            return result

    # ─── Aggregated Summary (symbol-aware) ─────────────────────────────

    def _extract_coin(self, symbol: str) -> str:
        """Pull coin ticker from a contract symbol e.g. 'BTC/USDT:USDT' -> 'BTC'."""
        if not symbol:
            return "BTC"
        return symbol.split('/')[0].upper()

    async def get_summary(self, symbol: str = "BTC") -> NormalizedSentiment:
        """
        Aggregate on-chain data into a sentiment score for the given coin.
        Each chain uses different signals:
          BTC: market cap, BTC dominance, mempool congestion
          ETH: market cap, gas price (high gas = high demand), large transfers count
          SOL: market cap, TPS health, epoch info
        """
        coin = self._extract_coin(symbol)
        global_market = await self.get_global_market()
        sentiment_score = 0  # -100 (Bearish) to 100 (Bullish)
        details: Dict[str, Any] = {"coin": coin}

        # ── Global signals (apply to ALL coins) ──
        mc_change = global_market.get("market_cap_change_24h_pct", 0)
        if mc_change > 3:
            sentiment_score += 25
        elif mc_change > 0:
            sentiment_score += 10
        elif mc_change < -3:
            sentiment_score -= 25
        elif mc_change < 0:
            sentiment_score -= 10
        details["mc_change_24h"] = mc_change

        btc_dom = global_market.get("btc_dominance", 50)
        details["btc_dominance"] = btc_dom

        # ── Coin-specific signals ──
        if coin == "BTC":
            btc_stats = await self.get_btc_onchain_stats()
            # BTC dominance high = bullish for BTC itself (flight to safety)
            if btc_dom > 55:
                sentiment_score += 5
            elif btc_dom < 40:
                sentiment_score -= 5
            # Mempool congestion = high demand = bullish
            unconfirmed = btc_stats.get("unconfirmed_txs", 0)
            if unconfirmed > 100000:
                sentiment_score += 10
            elif unconfirmed > 50000:
                sentiment_score += 5
            details.update({
                "hash_rate": btc_stats.get("hash_rate", 0),
                "unconfirmed_txs": unconfirmed,
            })

        elif coin == "ETH":
            # BTC dominance high = bad for ETH (capital leaving alts)
            if btc_dom > 55:
                sentiment_score -= 8
            elif btc_dom < 40:
                sentiment_score += 8

            gas = await self.get_eth_gas_price()
            avg_gas = gas.get("average", 0)
            # High gas = high demand = bullish
            if avg_gas > 80:
                sentiment_score += 12
            elif avg_gas > 40:
                sentiment_score += 6
            elif avg_gas < 15:
                sentiment_score -= 5  # network quiet
            details["avg_gas_gwei"] = avg_gas

            # Large whale transfers signal momentum
            whales = await self.get_eth_large_transfers(min_value_eth=500.0)
            whale_count = len(whales)
            if whale_count > 5:
                sentiment_score += 8
            elif whale_count > 2:
                sentiment_score += 4
            details["whale_transfers"] = whale_count

        elif coin == "SOL":
            # Alt-friendly conditions
            if btc_dom > 55:
                sentiment_score -= 10  # SOL hurt more than ETH when BTC dominates
            elif btc_dom < 40:
                sentiment_score += 10

            sol_stats = await self.get_sol_onchain_stats()
            tps = sol_stats.get("tps", 0)
            # Solana network health: healthy TPS = bullish
            # Normal TPS range: 1500-3000. Low TPS suggests congestion/issues.
            if tps > 2500:
                sentiment_score += 12
            elif tps > 1500:
                sentiment_score += 6
            elif tps < 800:
                sentiment_score -= 10  # network struggling
            details.update({
                "tps": tps,
                "slot_height": sol_stats.get("slot_height", 0),
            })
        else:
            # Unknown coin — use market-wide signals only
            details["note"] = f"No specific on-chain signals available for {coin}, using market-wide data"

        # Classify
        classification = "Neutral"
        if sentiment_score >= 20:
            classification = "Bullish"
        elif sentiment_score <= -20:
            classification = "Bearish"

        logger.info("onchain_summary_built", coin=coin, score=sentiment_score, classification=classification)
        return NormalizedSentiment(
            source=f"onchain_{coin.lower()}",
            score=sentiment_score,
            classification=classification,
            timestamp=datetime.now(),
        )
