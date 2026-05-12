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
        base_url: Optional[str] = None,
    ):
        self.exchange_name = exchange_name or settings.EXCHANGE_NAME
        self.api_key = api_key or settings.EXCHANGE_API_KEY
        self.api_secret = api_secret or settings.EXCHANGE_API_SECRET
        self.testnet = testnet if testnet is not None else settings.EXCHANGE_TESTNET
        self.base_url = base_url

        self.exchange = self._create_exchange()
        logger.info("exchange_initialized",
            exchange=self.exchange_name,
            testnet=self.testnet,
            demo=getattr(self.exchange, 'demo', False)
        )

    async def switch_profile(self, profile: str, api_key: str, api_secret: str, base_url: Optional[str] = None):
        """Hot-swap exchange connection to a new profile."""
        # 1. Close old connection
        if hasattr(self, 'exchange') and self.exchange:
            await self.exchange.close()
        
        # 2. Update credentials
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        
        is_demo_trading = base_url and "api-demo.bybit.com" in base_url
        self.testnet = (profile == "demo" and not is_demo_trading)
        
        # 3. Re-create CCXT instance
        self.exchange = self._create_exchange()
        # Even with demo=True, we explicitly set the URL if provided
        if base_url:
            if isinstance(self.exchange.urls.get('api'), dict):
                for k in self.exchange.urls['api']:
                    self.exchange.urls['api'][k] = base_url
            else:
                self.exchange.urls['api'] = base_url
            
        logger.info("exchange_profile_switched", profile=profile, testnet=self.testnet, base_url=base_url)

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

        if self.api_key:
            config["apiKey"] = self.api_key
        if self.api_secret:
            config["secret"] = self.api_secret

        # Initialize the specific exchange class
        exchange = exchange_class(config)

        # Detect Bybit Demo Trading (api-demo.bybit.com)
        self.is_bybit_demo = (
            self.exchange_name == 'bybit'
            and self.base_url
            and "api-demo.bybit.com" in self.base_url
        )

        if self.is_bybit_demo:
            # Use CCXT's official Bybit Demo Trading method.
            # This correctly routes private calls to api-demo.bybit.com
            # while keeping public market data on Mainnet.
            exchange.enable_demo_trading(True)
            logger.info("bybit_demo_trading_enabled_via_official_method")
        elif self.testnet:
            exchange.set_sandbox_mode(True)
            logger.info("sandbox_mode_enabled", exchange=self.exchange_name)

        return exchange

    @log_integration(service_type="EXCHANGE", provider_name=settings.EXCHANGE_NAME, endpoint="fetch_ticker")
    async def get_ticker(self, symbol: str) -> dict:
        """
        Ambil harga terkini suatu pair.
        """
        from app.services.integration_logger import IntegrationLogger
        url = self.exchange.urls.get('api')
        if isinstance(url, dict): url = url.get('public') or str(url)
        IntegrationLogger.record_request(url=str(url), method="GET", body={"symbol": symbol})

        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            logger.info("ticker_fetched", symbol=symbol, price=ticker["last"])
            return ticker
        except Exception as e:
            logger.error("ticker_fetch_error", symbol=symbol, error=str(e))
            raise

    @log_integration(service_type="EXCHANGE", provider_name=settings.EXCHANGE_NAME, endpoint="fetch_ohlcv")
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        since: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> list:
        """
        Ambil data candlestick/OHLCV.
        """
        from app.services.integration_logger import IntegrationLogger
        url = self.exchange.urls.get('api')
        if isinstance(url, dict): url = url.get('public') or str(url)
        IntegrationLogger.record_request(url=str(url), method="GET", body={"symbol": symbol, "timeframe": timeframe, "limit": limit})
        
        try:
            return await self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)
        except Exception as e:
            logger.error("ohlcv_fetch_error", symbol=symbol, timeframe=timeframe, error=str(e))
            raise

    @log_integration(service_type="EXCHANGE", provider_name=settings.EXCHANGE_NAME, endpoint="fetch_balance")
    async def get_balance(self) -> dict:
        """Ambil saldo akun."""
        from app.services.integration_logger import IntegrationLogger
        url = self.exchange.urls.get('api')
        if isinstance(url, dict): url = url.get('private') or url.get('public') or str(url)
        IntegrationLogger.record_request(url=str(url), method="POST")

        try:
            # Bybit Unified Account (both demo and mainnet) requires accountType param
            if self.exchange_name == 'bybit':
                balance = await self.exchange.fetch_balance({'accountType': 'UNIFIED'})
            else:
                balance = await self.exchange.fetch_balance()
            return balance
        except Exception as e:
            logger.error("balance_fetch_error", error=str(e))
            raise

    @log_integration(service_type="EXCHANGE", provider_name=settings.EXCHANGE_NAME, endpoint="fetch_funding_rate")
    async def get_funding_rate(self, symbol: str) -> dict:
        """Ambil funding rate terbaru."""
        from app.services.integration_logger import IntegrationLogger
        url = self.exchange.urls.get('api')
        if isinstance(url, dict): url = url.get('public') or str(url)
        IntegrationLogger.record_request(url=str(url), method="GET", body={"symbol": symbol})

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
        from app.services.integration_logger import IntegrationLogger
        url = self.exchange.urls.get('api')
        if isinstance(url, dict): url = url.get('public') or str(url)
        IntegrationLogger.record_request(url=str(url), method="GET", body={"symbol": symbol})

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
