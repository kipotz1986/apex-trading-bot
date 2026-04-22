import asyncio
import traceback
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.core.factory import create_orchestrator
from app.models.risk_state import RiskState
from app.services.market_data import MarketDataService
from app.services.exchange import ExchangeService
from app.services.news_feed import NewsFeedService
from app.services.sentiment_data import SentimentDataService
from app.services.onchain_data import OnChainDataService
from app.schemas.portfolio import PortfolioState

logger = get_logger(__name__)

class BotRunner:
    """
    Background worker that runs the trading loop.
    """

    def __init__(self, interval_seconds: int = 60):
        self.interval = interval_seconds
        self.is_running = False
        self._task = None

    async def start(self):
        """Starts the background loop."""
        if self.is_running:
            return
        
        self.is_running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("bot_runner_started", interval=self.interval)

    async def stop(self):
        """Stops the background loop."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("bot_runner_stopped")

    async def _loop(self):
        """Main trading loop."""
        while self.is_running:
            db = SessionLocal()
            try:
                await self._step(db)
            except Exception as e:
                logger.error("bot_loop_error", error=str(e), trace=traceback.format_exc())
            finally:
                db.close()
            
            await asyncio.sleep(self.interval)

    async def _step(self, db: Session):
        """Single iteration of the bot logic."""
        # 1. Check system status
        risk_state = db.query(RiskState).first()
        if not risk_state or risk_state.system_status == "PAUSED":
            # logger.info("bot_step_skipped", reason="paused_or_uninitialized")
            return

        logger.info("bot_step_started", mode="LIVE" if risk_state.is_live_enabled else "PAPER")

        # 2. Initialize Orchestrator and data services
        orchestrator = create_orchestrator(db)
        from app.core.factory import ServiceFactory
        factory = ServiceFactory.get_orchestrator(db) # This ensures singleton is created
        
        exchange = ServiceFactory._instance.exchange
        market = MarketDataService(exchange)
        news = NewsFeedService()
        sentiment_data = SentimentDataService(exchange)
        onchain = OnChainDataService()

        # 3. Gather Data for a set of symbols (e.g. BTC/USDT)
        # In a real app, this would be a list of symbols from settings
        # Using CCXT unified format for Swap/Perpetual: BASE/QUOTE:SETTLE
        symbols = ["BTC/USDT:USDT"] 

        for symbol in symbols:
            try:
                # Parallel data gathering with individual error handling
                coin = symbol.split('/')[0]
                
                async def safe_gather(task, name, default):
                    try:
                        return await task
                    except Exception as te:
                        logger.warning(f"data_gathering_failed_{name}", symbol=symbol, error=str(te))
                        return default

                # Start tasks
                candles_task = safe_gather(market.get_multi_timeframe_candles(symbol), "candles", {})
                news_task = safe_gather(news.get_latest_news(currencies=[coin]), "news", [])
                sentiment_task = safe_gather(sentiment_data.get_composite_sentiment(symbol), "sentiment", None)
                onchain_summary_task = safe_gather(onchain.get_summary(coin), "onchain_summary", None)
                onchain_stats_task = safe_gather(onchain.get_btc_onchain_stats(), "onchain_stats", {}) if coin == "BTC" else asyncio.sleep(0, {})

                candles, news_list, composite_sentiment, onchain_summary, onchain_stats = await asyncio.gather(
                    candles_task, news_task, sentiment_task, onchain_summary_task, onchain_stats_task
                )

                if not candles:
                    logger.error("bot_step_skipped_no_candles", symbol=symbol)
                    continue

                market_data = {
                    "candles": candles,
                    "news": news_list,
                    "composite_sentiment": composite_sentiment,
                    "onchain_summary": onchain_summary,
                    "onchain_stats": onchain_stats
                }

                # 4. Get Portfolio State
                # Simplified: current equity from risk_state
                equity = risk_state.current_equity or 10000.0
                portfolio = PortfolioState(
                    total_balance=equity,
                    total_equity=equity,
                    available_margin=equity,
                    open_positions=[],
                    daily_pnl_pct=0.0,
                    weekly_pnl_pct=0.0,
                    max_drawdown_pct=0.0
                )

                # 5. EXECUTE DECISION
                decision = await orchestrator.decide(symbol, market_data, portfolio)
                
                logger.info("bot_step_decision_complete", 
                    symbol=symbol, 
                    action=decision.action, 
                    confidence=decision.confidence
                )

            except Exception as se:
                logger.error("bot_step_symbol_failed", symbol=symbol, error=str(se))

# Singleton instance
bot_runner = BotRunner(interval_seconds=60)
