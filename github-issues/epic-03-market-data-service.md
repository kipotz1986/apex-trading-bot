# Epic 3: Market Data Service

---

## T-3.1: Integrasi CCXT Library untuk Koneksi Exchange

**Labels:** `epic-3`, `market-data`, `integration`, `priority-critical`
**Milestone:** Fase 1 — Foundation

### Deskripsi
Mengintegrasi library CCXT (CryptoCurrency eXchange Trading) sebagai unified interface untuk berkomunikasi dengan berbagai exchange (Bybit, Binance, OKX). CCXT menyediakan satu API yang sama untuk 100+ exchange, sehingga kita tidak perlu menulis kode berbeda untuk setiap exchange.

### Apa itu CCXT?
CCXT adalah library Python yang menyediakan fungsi-fungsi standar untuk berinteraksi dengan banyak exchange kripto. Misalnya, `exchange.fetch_ticker("BTC/USDT")` akan bekerja di Bybit, Binance, maupun OKX — kodenya persis sama.

### Langkah-Langkah Implementasi

#### 1. Install dependency
```bash
pip install ccxt
echo "ccxt>=4.3.0" >> backend/requirements.txt
```

#### 2. Buat file `backend/app/services/exchange.py`

```python
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
            "apiKey": self.api_key,
            "secret": self.api_secret,
            "enableRateLimit": True,  # Otomatis handle rate limiting
            "options": {
                "defaultType": "swap",  # Futures/perpetual
            },
        }

        exchange = exchange_class(config)

        # Aktifkan testnet/sandbox jika paper trading
        if self.testnet:
            exchange.set_sandbox_mode(True)
            logger.info("sandbox_mode_enabled", exchange=self.exchange_name)

        return exchange

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

    async def get_balance(self) -> dict:
        """Ambil saldo akun."""
        try:
            balance = await self.exchange.fetch_balance()
            return balance
        except Exception as e:
            logger.error("balance_fetch_error", error=str(e))
            raise

    async def close(self):
        """Tutup koneksi ke exchange. Panggil saat app shutdown."""
        await self.exchange.close()
```

#### 3. Verifikasi (tanpa API key, hanya public API)
```python
import asyncio
import ccxt.async_support as ccxt

async def test():
    exchange = ccxt.bybit({"enableRateLimit": True})
    ticker = await exchange.fetch_ticker("BTC/USDT")
    print(f"BTC/USDT Price: ${ticker['last']}")
    await exchange.close()

asyncio.run(test())
```

### Definition of Done
- [ ] CCXT library terinstall dan masuk `requirements.txt`
- [ ] `ExchangeService` bisa membuat koneksi ke Bybit, Binance, OKX
- [ ] Sandbox/testnet mode bisa diaktifkan untuk paper trading
- [ ] `get_ticker()` berhasil mengambil harga
- [ ] Rate limiting otomatis aktif
- [ ] Proper error handling + logging

### File yang Dibuat
- `[NEW]` `backend/app/services/exchange.py`

---

## T-3.2: Service Pengambilan Data Candlestick Historis

**Labels:** `epic-3`, `market-data`, `data-pipeline`, `priority-critical`
**Milestone:** Fase 1 — Foundation
**Depends On:** T-3.1

### Deskripsi
Membuat service untuk mengunduh data candle/OHLCV (Open, High, Low, Close, Volume) dari exchange. Data ini adalah input utama untuk analisa teknikal. Harus mendukung beberapa timeframe karena professional trader menganalisis di banyak timeframe sekaligus.

### Apa itu Candlestick / OHLCV?
Setiap "candle" merepresentasikan pergerakan harga dalam 1 periode waktu:
- **Open:** Harga pembukaan periode
- **High:** Harga tertinggi dalam periode
- **Low:** Harga terendah dalam periode
- **Close:** Harga penutupan periode
- **Volume:** Total volume perdagangan dalam periode

Timeframe 1H berarti 1 candle = 1 jam data. Timeframe 4H berarti 1 candle = 4 jam.

### Langkah-Langkah Implementasi

#### 1. Buat file `backend/app/services/market_data.py`

```python
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
```

### Definition of Done
- [ ] `get_candles()` mengambil data OHLCV dari exchange
- [ ] Multi-timeframe (15m, 1h, 4h, 1d) didukung
- [ ] `get_multi_timeframe_candles()` mengambil semua TF sekaligus
- [ ] Data di-convert ke format dict yang rapi (bukan raw array)
- [ ] Error handling + logging

### File yang Dibuat
- `[NEW]` `backend/app/services/market_data.py`

---

## T-3.3: WebSocket Stream untuk Data Harga Real-time

**Labels:** `epic-3`, `market-data`, `real-time`, `priority-high`
**Milestone:** Fase 1 — Foundation
**Depends On:** T-3.1

### Deskripsi
Membuat koneksi WebSocket ke exchange untuk menerima update harga secara real-time (tanpa perlu polling/request berulang). Data ini digunakan untuk monitoring posisi dan trigger sinyal.

### Apa itu WebSocket?
HTTP biasa = request-response (tanya-jawab). WebSocket = koneksi terbuka terus-menerus, exchange bisa kirim update kapan saja tanpa kita minta. Jauh lebih cepat dan efisien.

### Langkah-Langkah Implementasi

#### 1. Buat file `backend/app/services/market_stream.py`

```python
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
                tickers = await self.exchange.exchange.watch_tickers(symbols)
                for symbol, ticker in tickers.items():
                    if symbol in self._callbacks:
                        for callback in self._callbacks[symbol]:
                            await callback(ticker)
            except Exception as e:
                logger.error("stream_error", error=str(e))
                await asyncio.sleep(5)  # Retry after 5 seconds

    async def stop(self):
        """Hentikan streaming."""
        self._running = False
        logger.info("stream_stopped")
```

### Definition of Done
- [ ] WebSocket stream bisa menerima data real-time dari exchange
- [ ] Callback system berfungsi (subscriber menerima update)
- [ ] Auto-reconnect saat koneksi terputus
- [ ] Bisa start dan stop stream

### File yang Dibuat
- `[NEW]` `backend/app/services/market_stream.py`

---

## T-3.4: Service Pengambilan Data On-Chain

**Labels:** `epic-3`, `market-data`, `fundamental`, `priority-medium`
**Milestone:** Fase 1 — Foundation

### Deskripsi
Mengambil data blockchain (on-chain) yang relevan untuk analisa fundamental. Data ini termasuk: pergerakan whale (pemilik aset besar), aliran dana masuk/keluar exchange, dan metrik jaringan.

### Apa itu Data On-Chain?
Data yang tercatat langsung di blockchain. Contoh penting:
- **Whale Alert:** Jika dompet besar mengirim 1000 BTC ke exchange → kemungkinan akan dijual → sinyal bearish
- **Exchange Inflow:** Banyak BTC masuk ke exchange → orang-orang mau jual → bearish
- **Exchange Outflow:** Banyak BTC keluar dari exchange → orang-orang hold → bullish

### Langkah-Langkah
1. Buat `backend/app/services/onchain_data.py`
2. Integrasi API pihak ketiga:
   - **Glassnode** (https://glassnode.com) — on-chain metrics
   - **WhaleAlert** (https://whale-alert.io) — monitoring whale transactions
   - **CryptoQuant** (https://cryptoquant.com) — exchange flow data
3. Minimal ambil data: exchange inflow/outflow dan whale movement
4. Sediakan fallback jika salah satu API tidak tersedia

### Definition of Done
- [ ] Data on-chain bisa diambil dari minimal 1 provider
- [ ] Format data dinormalisasi ke format internal
- [ ] Error handling jika API down

### File yang Dibuat
- `[NEW]` `backend/app/services/onchain_data.py`

---

## T-3.5: Service Pengambilan Berita Kripto

**Labels:** `epic-3`, `market-data`, `fundamental`, `priority-medium`
**Milestone:** Fase 1 — Foundation

### Deskripsi
Membuat service untuk mengambil berita kripto terkini yang akan digunakan oleh Fundamental Analyst Agent. Berita major (regulasi, hack, institutional adoption) sangat mempengaruhi harga.

### Langkah-Langkah
1. Buat `backend/app/services/news_feed.py`
2. Integrasi sumber berita:
   - **CryptoPanic API** (https://cryptopanic.com/developers/api/) — aggregator berita kripto dengan filter penting
   - **RSS Feed** dari CoinDesk, CoinTelegraph
3. Filter berita berdasarkan relevansi (BTC, ETH, major coins)
4. Setiap berita harus memiliki: title, source, timestamp, importance_level
5. Cache di Redis (berita yang sama tidak perlu diproses ulang)

### Definition of Done
- [ ] Berita terbaru bisa diambil secara otomatis
- [ ] Format output: `[{title, source, url, timestamp, importance}]`
- [ ] Caching aktif (hindari redundansi)
- [ ] Rate limiting ditangani

### File yang Dibuat
- `[NEW]` `backend/app/services/news_feed.py`

---

## T-3.6: Service Pengambilan Sentimen Pasar

**Labels:** `epic-3`, `market-data`, `sentiment`, `priority-medium`
**Milestone:** Fase 1 — Foundation

### Deskripsi
Mengambil indikator sentimen pasar untuk Sentiment Analyst Agent. Sentimen menggambarkan "mood" pasar — apakah orang-orang optimis atau pesimis.

### Data Sentimen yang Diambil
| Data | Sumber | Penjelasan |
|---|---|---|
| **Fear & Greed Index** | alternative.me API | 0 = Extreme Fear (biasanya beli), 100 = Extreme Greed (biasanya jual) |
| **Funding Rate** | Exchange API (CCXT) | Positif = banyak Long, Negatif = banyak Short |
| **Open Interest** | Exchange API (CCXT) | Total posisi terbuka di market |
| **Long/Short Ratio** | Exchange API | Rasio trader yang Long vs Short |

### Langkah-Langkah
1. Buat `backend/app/services/sentiment_data.py`
2. Implementasi fetcher untuk setiap data di tabel di atas
3. Agregasi menjadi skor sentimen tunggal (-100 s/d +100)
4. Cache di Redis (update setiap 15 menit)

### Definition of Done
- [ ] Fear & Greed Index diambil dari API
- [ ] Funding Rate diambil dari exchange
- [ ] Open Interest diambil dari exchange
- [ ] Skor sentimen teragregasi
- [ ] Caching 15 menit

### File yang Dibuat
- `[NEW]` `backend/app/services/sentiment_data.py`

---

## T-3.7: Penyimpanan Data Time-Series ke TimescaleDB

**Labels:** `epic-3`, `database`, `data-pipeline`, `priority-high`
**Milestone:** Fase 1 — Foundation
**Depends On:** T-3.2, T-1.3

### Deskripsi
Menyimpan data candlestick ke TimescaleDB dengan retention policy otomatis. TimescaleDB adalah extension PostgreSQL yang dioptimasi untuk data time-series (data yang terurut berdasarkan waktu).

### Mengapa Perlu Disimpan?
1. Backtesting membutuhkan data historis yang banyak
2. Self-learning perlu data masa lalu untuk training
3. Mengurangi panggilan API ke exchange (ambil dari DB jika sudah ada)

### Langkah-Langkah
1. Buat migration: tabel `candles` yang hypertable (TimescaleDB)
2. Schema: `timestamp, symbol, timeframe, open, high, low, close, volume`
3. Indexing: composite index pada `(symbol, timeframe, timestamp)`
4. Retention policy: data 15m dihapus setelah 30 hari, 1h setelah 90 hari, 4h & 1d disimpan selamanya
5. Fungsi upsert: insert new, skip jika sudah ada (hindari duplikasi)

### Definition of Done
- [ ] Tabel `candles` sebagai hypertable di TimescaleDB
- [ ] Insert candle data berhasil
- [ ] Query by symbol + timeframe + time range berhasil
- [ ] Retention policy aktif
- [ ] Tidak ada data duplikat

### File yang Dibuat
- `[NEW]` `backend/app/models/candle.py`
- `[NEW]` `backend/app/services/candle_storage.py`

---

## T-3.8: Data Normalization Layer

**Labels:** `epic-3`, `data-pipeline`, `architecture`, `priority-medium`
**Milestone:** Fase 1 — Foundation
**Depends On:** T-3.1 s/d T-3.7

### Deskripsi
Membuat lapisan normalisasi yang memastikan semua data dari berbagai sumber memiliki format yang konsisten sebelum diberikan ke agent. Setiap exchange mungkin mengembalikan format berbeda — layer ini memastikan agent selalu menerima format yang sama.

### Langkah-Langkah
1. Buat `backend/app/services/data_normalizer.py`
2. Definisikan standardized schemas menggunakan Pydantic:
   - `NormalizedCandle(timestamp, open, high, low, close, volume)`
   - `NormalizedTicker(symbol, price, bid, ask, volume_24h, change_24h)`
   - `NormalizedSentiment(fear_greed, funding_rate, open_interest, long_short_ratio, composite_score)`
   - `NormalizedNews(title, source, timestamp, sentiment_score, importance)`
3. Semua service (T-3.1 s/d T-3.7) harus return data melalui normalizer ini

### Definition of Done
- [ ] Pydantic schemas untuk semua tipe data terdefinisi
- [ ] Data dari exchange di-normalize sebelum dikirim ke agent
- [ ] Validasi otomatis (invalid data ditolak)

### File yang Dibuat
- `[NEW]` `backend/app/services/data_normalizer.py`
- `[NEW]` `backend/app/schemas/market_data.py`
