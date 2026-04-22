"""
Exchange Connection Service.

Mengelola koneksi ke exchange kripto menggunakan CCXT.
Mendukung: Bybit (P0), Binance (P1), OKX (P2).

Usage:
    from app.services.exchange import ExchangeService
    exchange = ExchangeService()
    ticker = await exchange.get_ticker("BTC/USDT")
"""

import ccxt.async_support as ccxt
from app.core.config import settings
from app.core.logging import get_logger
from typing import Optional
from app.services.integration_logger import log_integration

logger = get_logger(__name__)


class ExchangeService:
    """Service untuk interaksi dengan exchange kripto."""

    def __init__(
        self,
        exchange_name: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: Optional[bool] = None,
    ):
        self.exchange_name = exchange_name or settings.EXCHANGE_NAME
        self.api_key = api_key or settings.EXCHANGE_API_KEY
        self.api_secret = api_secret or settings.EXCHANGE_API_SECRET
        self.testnet = testnet if testnet is not None else settings.EXCHANGE_TESTNET

        self.exchange = self._create_exchange()
        logger.info("exchange_initialized",
            exchange=self.exchange_name,
            testnet=self.testnet
        )

    def _create_exchange(self) -> ccxt.Exchange:
        """Buat instance exchange berdasarkan nama."""
        exchange_class = getattr(ccxt, self.exchange_name, None)
        if exchange_class is None:
            raise ValueError(f"Exchange '{self.exchange_name}' tidak didukung oleh CCXT")

        config = {
            "enableRateLimit": True,
            "options": {
                "defaultType": "swap",
            },
        }

        # Only add keys if they look real and are not the known invalid one
        invalid_key = "sR3NDllu2JgwqAFzPv"
        if self.api_key and not self.api_key.startswith("your_") and self.api_key != invalid_key:
            config["apiKey"] = self.api_key
        if self.api_secret and not self.api_secret.startswith("your_") and "jseU" not in self.api_secret:
            config["secret"] = self.api_secret

        # Initialize the specific exchange class
        exchange = exchange_class(config)

        # Aktifkan testnet/sandbox jika paper trading
        if self.testnet:
            exchange.set_sandbox_mode(True)
            logger.info("sandbox_mode_enabled", exchange=self.exchange_name)

        return exchange

    @log_integration(service_type="EXCHANGE", provider_name=settings.EXCHANGE_NAME, endpoint="fetch_ticker")
    async def get_ticker(self, symbol: str) -> dict:
        """
        Ambil harga terkini suatu pair.
        
        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
        
        Returns:
            dict dengan keys: last, bid, ask, high, low, volume, dll.
        """
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            logger.info("ticker_fetched", symbol=symbol, price=ticker["last"])
            return ticker
        except Exception as e:
            logger.error("ticker_fetch_error", symbol=symbol, error=str(e))
            raise

    @log_integration(service_type="EXCHANGE", provider_name=settings.EXCHANGE_NAME, endpoint="fetch_balance")
    async def get_balance(self) -> dict:
        """Ambil saldo akun."""
        try:
            balance = await self.exchange.fetch_balance()
            return balance
        except Exception as e:
            logger.error("balance_fetch_error", error=str(e))
            raise

    @log_integration(service_type="EXCHANGE", provider_name=settings.EXCHANGE_NAME, endpoint="fetch_funding_rate")
    async def get_funding_rate(self, symbol: str) -> dict:
        """Ambil funding rate terbaru."""
        try:
            return await self.exchange.fetch_funding_rate(symbol)
        except (ccxt.BadSymbol, ccxt.NotSupported) as e:
            logger.warning("funding_rate_not_supported", symbol=symbol, error=str(e))
            return {}
        except Exception as e:
            logger.error("funding_rate_fetch_error", symbol=symbol, error=str(e))
            raise

    @log_integration(service_type="EXCHANGE", provider_name=settings.EXCHANGE_NAME, endpoint="fetch_open_interest")
    async def get_open_interest(self, symbol: str) -> dict:
        """Ambil open interest terbaru."""
        try:
            return await self.exchange.fetch_open_interest(symbol)
        except (ccxt.BadSymbol, ccxt.NotSupported) as e:
            logger.warning("open_interest_not_supported", symbol=symbol, error=str(e))
            return {}
        except Exception as e:
            logger.error("open_interest_fetch_error", symbol=symbol, error=str(e))
            raise

    async def close(self):
        """Tutup koneksi ke exchange. Panggil saat app shutdown."""
        await self.exchange.close()
