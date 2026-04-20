"""
Market Data Stream (WebSocket).

Menerima update harga real-time dari exchange via WebSocket.
Data di-broadcast ke internal consumers (agents, dashboard, dll).

Usage:
    stream = MarketStreamService(exchange_service)
    await stream.subscribe("BTC/USDT", callback=on_price_update)
    await stream.start()
"""

import asyncio
from typing import Callable, Any
from app.services.exchange import ExchangeService
from app.core.logging import get_logger

logger = get_logger(__name__)


class MarketStreamService:
    """Service untuk streaming data harga real-time via WebSocket."""

    def __init__(self, exchange: ExchangeService):
        self.exchange = exchange
        self._callbacks: dict[str, list[Callable]] = {}
        self._running = False

    async def subscribe(self, symbol: str, callback: Callable):
        """
        Daftarkan callback function yang akan dipanggil
        setiap kali harga symbol berubah.
        
        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            callback: Async function yang menerima ticker data
        """
        if symbol not in self._callbacks:
            self._callbacks[symbol] = []
        self._callbacks[symbol].append(callback)
        logger.info("stream_subscribed", symbol=symbol)

    async def start(self):
        """Mulai streaming. Blocking — jalankan di background task."""
        self._running = True
        symbols = list(self._callbacks.keys())
        logger.info("stream_starting", symbols=symbols)

        while self._running:
            try:
                # Gunakan CCXT watch_tickers untuk WebSocket
                # Pastikan exchange pendukung pro/websocket tersedia
                if not hasattr(self.exchange.exchange, 'watch_tickers'):
                    logger.error("exchange_no_websocket_support", exchange=self.exchange.exchange_name)
                    # Jika tidak ada websocket support, bisa polling sebagai fallback atau raise error
                    raise NotImplementedError(f"Exchange {self.exchange.exchange_name} does not support WebSockets via CCXT")

                tickers = await self.exchange.exchange.watch_tickers(symbols)
                for symbol, ticker in tickers.items():
                    if symbol in self._callbacks:
                        for callback in self._callbacks[symbol]:
                            await callback(ticker)
            except Exception as e:
                logger.error("stream_error", error=str(e))
                # Tunggu sebentar sebelum reconnect
                await asyncio.sleep(5)

    async def stop(self):
        """Hentikan streaming."""
        self._running = False
        logger.info("stream_stopped")
        # Catatan: Kita mungkin perlu menutup koneksi WS spesifik jika CCXT tidak mengurusnya saat loop berhenti
