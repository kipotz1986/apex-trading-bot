import asyncio
import json
import websockets
from typing import Set
from app.core.config import settings
from app.core.logging import get_logger
from app.api.websocket import broadcast_updates
from app.core.database import SessionLocal
from app.models.risk_state import RiskState
from app.models.order import Order
from datetime import datetime

logger = get_logger(__name__)

# Candlestick chart symbols and their Bybit WS symbol names
CHART_SYMBOLS = {
    "BTC/USDT": "BTCUSDT",
    "ETH/USDT": "ETHUSDT",
    "SOL/USDT": "SOLUSDT",
    "XRP/USDT": "XRPUSDT",
}

# Bybit kline intervals to subscribe: 1m, 5m, 15m, 1h, 4h
KLINE_INTERVALS = ["1", "5", "15", "60", "240"]


class MarketStreamService:
    """
    Streams real-time market data (tickers + klines) from Bybit and broadcasts
    via internal WebSocket to the frontend.

    Channels emitted:
      • market_prices — tick price for open-position symbols
      • portfolio_update — equity/balance snapshot every 5 s
      • kline — OHLCV candle updates for BTC/ETH/SOL/XRP
    """

    def __init__(self):
        self.url = "wss://stream.bybit.com/v5/public/linear"
        self.is_running = False
        self._task = None
        self._equity_task = None
        self.subscribed_symbols: Set[str] = set()
        self.last_prices = {}
        self.last_db_snapshot = 0

    async def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._task = asyncio.create_task(self._run())
        self._equity_task = asyncio.create_task(self._equity_loop())
        logger.info("market_stream_service_started")

    async def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
        if self._equity_task:
            self._equity_task.cancel()
        logger.info("market_stream_service_stopped")

    async def _equity_loop(self):
        """Dedicated loop for broadcasting equity snapshots every 5 s."""
        while self.is_running:
            try:
                now = asyncio.get_event_loop().time()
                save = now - self.last_db_snapshot > 60
                if save:
                    self.last_db_snapshot = now
                await self._broadcast_equity_update(save_to_db=save)
                await asyncio.sleep(5)
            except Exception as e:
                logger.error("equity_loop_error", error=str(e))
                await asyncio.sleep(5)

    async def _run(self):
        while self.is_running:
            try:
                async with websockets.connect(self.url, ping_interval=None) as ws:
                    logger.info("connected_to_bybit_websocket")

                    # ── Ticker subscriptions (active trading symbols + open positions) ──
                    db = SessionLocal()
                    open_orders = db.query(Order).filter(Order.status.in_(["OPEN", "FILLED"])).all()
                    active_symbols = set(settings.get_symbol_list())
                    for op in open_orders:
                        active_symbols.add(op.symbol)
                    db.close()

                    bybit_ticker_syms = [s.replace("/", "").split(":")[0] for s in active_symbols]
                    if bybit_ticker_syms:
                        await ws.send(json.dumps({
                            "op": "subscribe",
                            "args": [f"tickers.{s}" for s in bybit_ticker_syms]
                        }))
                        logger.info("subscribed_to_tickers", symbols=bybit_ticker_syms)

                    # ── Kline subscriptions (BTC / ETH / SOL, all intervals) ──
                    # Bybit allows max 10 args per subscription message, so batch them.
                    kline_topics = [
                        f"kline.{interval}.{bybit_sym}"
                        for bybit_sym in CHART_SYMBOLS.values()
                        for interval in KLINE_INTERVALS
                    ]
                    # Send in batches of 10
                    for i in range(0, len(kline_topics), 10):
                        await ws.send(json.dumps({
                            "op": "subscribe",
                            "args": kline_topics[i:i + 10]
                        }))
                    logger.info("subscribed_to_klines", count=len(kline_topics))

                    # ── Message loop ──
                    while self.is_running:
                        try:
                            message = await asyncio.wait_for(ws.recv(), timeout=20)
                            data = json.loads(message)

                            topic = data.get("topic", "")

                            if topic.startswith("tickers."):
                                await self._handle_ticker(data, topic)

                            elif topic.startswith("kline."):
                                await self._handle_kline(data, topic)

                        except asyncio.TimeoutError:
                            await ws.send(json.dumps({"op": "ping"}))
                        except Exception as e:
                            logger.error("market_stream_loop_error", error=str(e))
                            break

            except Exception as e:
                logger.error("market_stream_connection_error", error=str(e))
                await asyncio.sleep(5)

    async def _handle_ticker(self, data: dict, topic: str):
        """Process a tickers.SYMBOL message."""
        raw_symbol = topic.split(".")[1]
        formatted = (
            f"{raw_symbol[:-4]}/{raw_symbol[-4:]}:USDT"
            if raw_symbol.endswith("USDT")
            else raw_symbol
        )
        tick = data.get("data", {})
        if tick:
            last_price = tick.get("lastPrice")
            if last_price:
                self.last_prices[formatted] = float(last_price)
                await broadcast_updates("market_prices", {
                    "symbol": formatted,
                    "price": float(last_price),
                    "timestamp": data.get("ts"),
                })

    async def _handle_kline(self, data: dict, topic: str):
        """
        Process a kline.{interval}.{SYMBOL} message and broadcast to the
        'kline' channel.

        Frontend expects:
          { symbol, timeframe, candle: { time, open, high, low, close, volume, confirmed } }

        lightweight-charts uses Unix seconds for 'time'; Bybit sends milliseconds.
        """
        parts = topic.split(".")          # ["kline", "1", "BTCUSDT"]
        if len(parts) < 3:
            return
        interval = parts[1]
        bybit_sym = parts[2]

        # Reverse-lookup display symbol
        display_sym = next(
            (k for k, v in CHART_SYMBOLS.items() if v == bybit_sym),
            bybit_sym
        )

        candles = data.get("data", [])
        if not candles:
            return

        for kline in candles:
            start_ms = kline.get("start")
            if start_ms is None:
                continue
            await broadcast_updates("kline", {
                "symbol": display_sym,
                "timeframe": interval,
                "candle": {
                    "time": int(start_ms) // 1000,          # seconds
                    "open":   float(kline.get("open", 0)),
                    "high":   float(kline.get("high", 0)),
                    "low":    float(kline.get("low", 0)),
                    "close":  float(kline.get("close", 0)),
                    "volume": float(kline.get("volume", 0)),
                    "confirmed": bool(kline.get("confirm", False)),
                },
            })

    async def _broadcast_equity_update(self, save_to_db: bool = False):
        """Calculates current equity, broadcasts it, and optionally saves to DB."""
        db = SessionLocal()
        try:
            from app.models.risk_snapshot import RiskSnapshot
            from sqlalchemy import func
            from datetime import time

            risk_state = db.query(RiskState).first()
            if not risk_state:
                return

            is_paper_mode = not risk_state.is_live_enabled

            open_positions = db.query(Order).filter(
                Order.status.in_(["OPEN", "FILLED"]),
                Order.is_paper == is_paper_mode
            ).all()
            total_unrealized_pnl = 0.0

            for pos in open_positions:
                search_key = pos.symbol.replace("/", "").replace(":", "").upper()
                current_price = self.last_prices.get(pos.symbol)
                if not current_price:
                    for k, v in self.last_prices.items():
                        if search_key in k.replace("/", "").replace(":", "").upper():
                            current_price = v
                            break

                if current_price and pos.average_filled_price:
                    is_long = pos.side in ["LONG", "BUY"]
                    pnl = (current_price - pos.average_filled_price) * pos.requested_amount * (1 if is_long else -1)
                    total_unrealized_pnl += pnl

            today_start = datetime.combine(datetime.now().date(), time.min)
            daily_closed_pnl = db.query(func.sum(Order.pnl_usd)).filter(
                Order.status == "CLOSED",
                Order.updated_at >= today_start,
                Order.is_paper == is_paper_mode
            ).scalar() or 0.0

            current_equity = risk_state.current_equity + total_unrealized_pnl
            current_balance = risk_state.current_equity

            await broadcast_updates("portfolio_update", {
                "equity": round(current_equity, 2),
                "balance": round(current_balance, 2),
                "unrealized_pnl": round(total_unrealized_pnl, 2),
                "daily_pnl": round(daily_closed_pnl + total_unrealized_pnl, 2),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })

            if save_to_db:
                snapshot = RiskSnapshot(
                    timestamp=datetime.utcnow(),
                    equity=current_equity,
                    balance=current_balance,
                    drawdown_pct=0.0,
                    is_paper=is_paper_mode,
                )
                db.add(snapshot)
                db.commit()
                logger.debug("equity_snapshot_saved", equity=current_equity, is_paper=is_paper_mode)

        except Exception as e:
            logger.error("equity_broadcast_failed", error=str(e))
        finally:
            db.close()


# Singleton instance
market_stream = MarketStreamService()
