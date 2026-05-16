import asyncio
import traceback
from datetime import datetime, timedelta, time, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.api.websocket import broadcast_updates
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.core.factory import create_orchestrator
from app.models.risk_state import RiskState
from app.models.decision_log import DecisionLog
from app.models.order import Order
from app.models.system_settings import SystemSettings
from app.services.market_data import MarketDataService
from app.services.exchange import ExchangeService
from app.services.news_feed import NewsFeedService
from app.services.sentiment_data import SentimentDataService
from app.services.onchain_data import OnChainDataService
from app.services.position_monitor import PositionMonitor
from app.services.telegram import TelegramService
from app.schemas.portfolio import PortfolioState
from app.core.config import settings

logger = get_logger(__name__)


class BotRunner:
    """
    Background worker that runs the trading loop.
    """

    def __init__(self, interval_seconds: int = None):
        self.interval = interval_seconds or settings.BOT_INTERVAL_SECONDS
        self.is_running = False
        self._task = None
        self._last_training_time = None
        self._training_in_progress = False
        self.current_step = "idle"  # Track current execution step

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

    async def _check_and_run_training(self):
        """Checks if it's time to run the 12-hour training cycle."""
        if self._training_in_progress:
            return

        now = datetime.utcnow()
        # Run every 12 hours
        if self._last_training_time is None or (now - self._last_training_time).total_seconds() >= 12 * 3600:
            self._training_in_progress = True
            logger.info("scheduled_training_triggered", last_run=self._last_training_time)
            try:
                from scripts.nightly_trainer import run_nightly_training
                # Run in background to avoid blocking the trading loop
                asyncio.create_task(self._execute_training_task(run_nightly_training))
            except Exception as e:
                logger.error("failed_to_trigger_training", error=str(e))
                self._training_in_progress = False

    async def _execute_training_task(self, training_func):
        """Wrapper to execute training and update status."""
        try:
            await training_func()
            self._last_training_time = datetime.utcnow()
            logger.info("scheduled_training_completed_successfully")
        except Exception as e:
            logger.error("scheduled_training_failed", error=str(e))
        finally:
            self._training_in_progress = False

    async def _loop(self):
        """Main trading loop."""
        while self.is_running:
            db = SessionLocal()
            try:
                # Refresh interval from DB if available
                db_interval = SystemSettings.get_value(db, "bot_interval_seconds")
                if db_interval:
                    try:
                        self.interval = int(db_interval)
                    except ValueError:
                        pass

                logger.info("bot_loop_heartbeat", interval=self.interval)

                # Run training check
                await self._check_and_run_training()
                # Daily summary check (07:00 WIB = 00:00 UTC)
                await self._check_and_send_daily_summary(db)
                # Run trading step
                await self._step(db)
                
                # Update last run time for countdown
                risk_state = db.query(RiskState).first()
                if risk_state:
                    risk_state.last_bot_run_at = datetime.utcnow()
                    db.commit()
                    logger.info("bot_run_time_updated", last_run=risk_state.last_bot_run_at)
            except Exception as e:
                logger.error("bot_loop_error", error=str(e), trace=traceback.format_exc())
            finally:
                db.close()

            await asyncio.sleep(self.interval)

    async def _check_and_send_daily_summary(self, db: Session):
        """Send Telegram daily summary at 07:00 WIB (00:00 UTC) once per day."""
        try:
            now_utc = datetime.utcnow()
            # 07:00 WIB == 00:00 UTC. Send within the first 5 minutes after midnight UTC.
            if now_utc.hour != 0 or now_utc.minute > 5:
                return

            today_key = now_utc.strftime("%Y-%m-%d")
            last_sent = SystemSettings.get_value(db, "telegram_last_daily_summary", "")
            if last_sent == today_key:
                return  # already sent today

            # Gather metrics
            risk_state = db.query(RiskState).first()
            if not risk_state:
                return
            equity = float(risk_state.current_equity or 0.0)
            mode = "LIVE" if risk_state.is_live_enabled else "PAPER"

            # PnL today: realized (closed orders since 00:00 UTC) + unrealized (open positions)
            today_start = datetime.combine(now_utc.date(), time.min)
            realized_today = db.query(func.sum(Order.pnl_usd)).filter(
                Order.status == "CLOSED",
                Order.closed_at >= today_start,
            ).scalar() or 0.0
            unrealized = db.query(func.sum(Order.pnl_usd)).filter(
                Order.status.in_(["OPEN", "FILLED"]),
            ).scalar() or 0.0
            pnl_today = float(realized_today) + float(unrealized)
            pnl_today_pct = (pnl_today / equity * 100) if equity > 0 else 0.0

            # Win rate over all closed trades
            total_closed = db.query(Order).filter(Order.status == "CLOSED").count()
            winning = db.query(Order).filter(Order.status == "CLOSED", Order.pnl_usd > 0).count()
            win_rate = (winning / total_closed * 100) if total_closed > 0 else 0.0

            trades_today = db.query(Order).filter(
                Order.created_at >= today_start,
            ).count()
            open_positions = db.query(Order).filter(Order.status.in_(["OPEN", "FILLED"])).count()

            telegram = TelegramService(db=db)
            sent = await telegram.send_daily_summary(
                equity=equity,
                pnl_today=pnl_today,
                pnl_today_pct=pnl_today_pct,
                win_rate=win_rate,
                trades_today=trades_today,
                open_positions=open_positions,
                mode=mode,
            )
            await telegram.close()

            if sent:
                SystemSettings.set_value(db, "telegram_last_daily_summary", today_key)
                logger.info("telegram_daily_summary_sent", date=today_key, equity=equity, pnl=pnl_today)
            else:
                logger.warning("telegram_daily_summary_send_failed", date=today_key)
        except Exception as e:
            logger.error("daily_summary_check_error", error=str(e))

    async def _sync_balance(self, db: Session, exchange: ExchangeService):
        """Sync actual exchange balance to RiskState."""
        try:
            balance = await exchange.get_balance()
            
            # Bybit Unified Account handling
            total_equity = 0.0
            
            # Try to get total equity from Bybit specific 'info' first
            if 'info' in balance and 'result' in balance['info'] and 'list' in balance['info']['result']:
                unified_data = balance['info']['result']['list'][0]
                total_equity = float(unified_data.get('totalEquity', 0.0))
            
            # Fallback to normalized USDT total if totalEquity is 0
            if total_equity <= 0 and 'total' in balance:
                total_equity = balance['total'].get('USDT', 0.0)
                # If they have USDC, add it too (simplified)
                total_equity += balance['total'].get('USDC', 0.0)
            
            if total_equity > 0:
                risk_state = db.query(RiskState).first()
                if risk_state:
                    risk_state.current_equity = total_equity
                    # Update peak if it's higher
                    if total_equity > (risk_state.equity_peak or 0):
                        risk_state.equity_peak = total_equity
                    db.commit()
                    logger.info("balance_synced", equity=total_equity)
            else:
                logger.warning("balance_sync_zero", balance_keys=list(balance.get('total', {}).keys()))
                
        except Exception as e:
            logger.error("balance_sync_failed", error=str(e))

    async def _step(self, db: Session):
        """Single iteration of the bot logic."""
        # 1. Initialize Orchestrator and data services
        from app.core.factory import create_orchestrator, ServiceFactory
        orchestrator = await create_orchestrator(db)
        factory = ServiceFactory._instance
        exchange = factory.exchange

        # 2. Sync Balance (Run even if paused to keep UI updated)
        await self._sync_balance(db, exchange)

        # 2.5 Sync Positions and Store Patterns for Self-Learning
        monitor = PositionMonitor(exchange, db, factory.pattern_memory)
        await monitor.sync_with_db()

        # 3. Check system status
        risk_state = db.query(RiskState).first()
        if not risk_state or risk_state.system_status == "PAUSED":
            logger.info("bot_step_skipped", 
                        reason="paused_or_uninitialized",
                        status=risk_state.system_status if risk_state else "MISSING")
            return

        logger.info("bot_step_started", mode="LIVE" if risk_state.is_live_enabled else "PAPER")
        await broadcast_updates("bot_progress", {"step": "fetching_data", "symbol": None})
        market = MarketDataService(exchange)
        news = NewsFeedService()
        sentiment_data = SentimentDataService(exchange)
        onchain = OnChainDataService()

        # 3. Gather Data for a set of symbols
        # Get from environment configuration
        symbols = settings.get_symbol_list()

        # 4. Get REAL Portfolio State ONCE per loop iteration
        # Moving this outside the loop prevents redundant API calls to Bybit for every symbol.
        try:
            portfolio = await self._get_portfolio_state(db, exchange, risk_state)
        except Exception as pe:
            logger.error("portfolio_state_unavailable_stopping_iteration", error=str(pe))
            return

        # Symbol-level executed flag — when a trade fires for symbol N, the next
        # symbol needs a fresh portfolio so exposure/margin reflect the new position.
        # Without this refresh, 4 symbols in one loop could each see "no exposure"
        # and collectively breach the profile's max_total_exposure cap.
        last_decision_executed = False

        for symbol in symbols:
            try:
                # Refresh portfolio if previous symbol opened/closed a position so
                # current_exposure and available_margin are accurate for this symbol.
                if last_decision_executed:
                    try:
                        portfolio = await self._get_portfolio_state(db, exchange, risk_state)
                        logger.info("portfolio_refreshed_mid_loop", symbol=symbol)
                    except Exception as pe:
                        logger.warning("portfolio_refresh_failed_using_stale", symbol=symbol, error=str(pe))
                    last_decision_executed = False

                # Parallel data gathering with individual error handling
                coin = symbol.split('/')[0]
                
                async def safe_gather(task, name, default):
                    try:
                        return await task
                    except Exception as te:
                        logger.warning(f"data_gathering_failed_{name}", symbol=symbol, error=str(te))
                        return default

                # Start tasks — each on-chain source is keyed to the actual coin
                candles_task = safe_gather(market.get_multi_timeframe_candles(symbol), "candles", {})
                news_task = safe_gather(news.get_latest_news(currencies=[coin]), "news", [])
                sentiment_task = safe_gather(sentiment_data.get_composite_sentiment(symbol), "sentiment", None)
                exchange_sentiment_task = safe_gather(sentiment_data.get_exchange_sentiment(symbol), "exchange_sentiment", {})
                onchain_summary_task = safe_gather(onchain.get_summary(symbol), "onchain_summary", None)

                # Coin-specific on-chain stats (BTC mempool, ETH gas, SOL TPS)
                async def _empty_onchain():
                    return {}
                if coin == "BTC":
                    stats_coro = onchain.get_btc_onchain_stats()
                elif coin == "ETH":
                    stats_coro = onchain.get_eth_gas_price()
                elif coin == "SOL":
                    stats_coro = onchain.get_sol_onchain_stats()
                elif coin == "XRP":
                    stats_coro = onchain.get_xrp_onchain_stats()
                else:
                    stats_coro = _empty_onchain()
                onchain_stats_task = safe_gather(stats_coro, "onchain_stats", {})

                candles, news_list, composite_sentiment, exchange_sentiment, onchain_summary, onchain_stats = await asyncio.gather(
                    candles_task, news_task, sentiment_task, exchange_sentiment_task, onchain_summary_task, onchain_stats_task
                )

                if not candles:
                    logger.error("bot_step_skipped_no_candles", symbol=symbol)
                    continue

                market_data = {
                    "candles": candles,
                    "news": news_list,
                    "composite_sentiment": composite_sentiment,
                    "exchange_sentiment": exchange_sentiment,  # ← FIXED: injected exchange data
                    "onchain_summary": onchain_summary,
                    "onchain_stats": onchain_stats
                }

                # 4.5 PAPER SL/TP ENFORCEMENT — close paper positions when their stored
                # stop_loss_price / take_profit_prices are crossed by the latest price.
                # Live positions are enforced by the exchange itself; paper trades had
                # no enforcement before this, which was the dominant cause of PF < 1.
                current_price = self._latest_close_from_candles(candles)
                if current_price > 0:
                    closed_count = await self._enforce_paper_sl_tp(
                        db, orchestrator, symbol, current_price
                    )
                    if closed_count > 0:
                        last_decision_executed = True  # portfolio is now stale

                # 5. EXECUTE DECISION
                decision = await orchestrator.decide(symbol, market_data, portfolio)

                logger.info("bot_step_decision_complete",
                    symbol=symbol,
                    action=decision.action,
                    confidence=decision.confidence
                )

                # Mark portfolio dirty if this decision opened or closed a position
                # (anything that mutates exchange/DB state). HOLD-only decisions don't.
                action_upper = (decision.action or "").upper()
                if action_upper in ("EXECUTE_LONG", "EXECUTE_SHORT", "CLOSE_LONG", "CLOSE_SHORT"):
                    last_decision_executed = True
                # Proactive closures route through executor inside orchestrator and
                # surface in the reasoning text — refresh portfolio if a close happened.
                elif "Proactive Closure" in (decision.reasoning or "") or "Exposure Relief" in (decision.reasoning or ""):
                    last_decision_executed = True

                # 6. Persist decision to DecisionLog (every decision, including HOLD)
                self._persist_decision(db, decision, symbol)

            except Exception as se:
                logger.error("bot_step_symbol_failed", symbol=symbol, error=str(se))
        
        await broadcast_updates("bot_progress", {"step": "idle", "symbol": None})

    def _latest_close_from_candles(self, candles: dict) -> float:
        """Pick the freshest close price from the available timeframe candles."""
        if not candles:
            return 0.0
        # Prefer shortest TF (most recent), fall back through coarser ones.
        for tf in ("1m", "5m", "15m", "1h", "4h"):
            tf_candles = candles.get(tf)
            if not tf_candles:
                continue
            last = tf_candles[-1]
            close = last.close if hasattr(last, "close") else (last.get("close") if isinstance(last, dict) else None)
            try:
                close_f = float(close) if close is not None else 0.0
                if close_f > 0:
                    return close_f
            except (TypeError, ValueError):
                continue
        # last resort: try any timeframe
        for tf_candles in candles.values():
            if not tf_candles:
                continue
            last = tf_candles[-1]
            close = last.close if hasattr(last, "close") else (last.get("close") if isinstance(last, dict) else None)
            try:
                close_f = float(close) if close is not None else 0.0
                if close_f > 0:
                    return close_f
            except (TypeError, ValueError):
                continue
        return 0.0

    async def _enforce_paper_sl_tp(self, db: Session, orchestrator, symbol: str, current_price: float) -> int:
        """
        Scan open paper positions for `symbol` and close them via the executor
        when stop_loss / take_profit are crossed by `current_price`.

        Routes through `orchestrator.executor.close_position` (rather than
        PaperTradingEngine.simulate_closure directly) so that learning events,
        WebSocket broadcasts, and Telegram alerts all fire consistently with
        any other close path.

        Returns: number of positions actually closed.
        """
        from app.models.order import Order
        try:
            paper_orders = (
                db.query(Order)
                .filter(
                    Order.symbol == symbol,
                    Order.is_paper == True,
                    Order.status == "FILLED",
                    Order.closed_at == None,
                )
                .all()
            )
        except Exception as e:
            logger.warning("paper_sl_tp_query_failed", symbol=symbol, error=str(e))
            return 0

        if not paper_orders:
            return 0

        closed = 0
        for order in paper_orders:
            sl = order.stop_loss_price
            tps = order.take_profit_prices or []
            side_upper = (order.side or "").upper()

            hit = False
            reason = ""
            if side_upper in ("BUY", "LONG"):
                # Long: SL below entry, TPs above
                if sl and current_price <= sl:
                    hit, reason = True, f"SL hit at {current_price:.4f} (sl={sl:.4f})"
                elif tps:
                    # close on the FIRST TP crossed (full close — partial TPs are a
                    # future enhancement requiring order-size accounting)
                    for tp in sorted(tps):
                        if current_price >= tp:
                            hit, reason = True, f"TP hit at {current_price:.4f} (tp={tp:.4f})"
                            break
            elif side_upper in ("SELL", "SHORT"):
                if sl and current_price >= sl:
                    hit, reason = True, f"SL hit at {current_price:.4f} (sl={sl:.4f})"
                elif tps:
                    for tp in sorted(tps, reverse=True):
                        if current_price <= tp:
                            hit, reason = True, f"TP hit at {current_price:.4f} (tp={tp:.4f})"
                            break

            if not hit:
                continue

            try:
                ok = await orchestrator.executor.close_position(
                    symbol=order.symbol,
                    side=order.side,
                    amount=order.requested_amount,
                    order_id=order.id,
                )
                if ok:
                    closed += 1
                    logger.info("paper_sl_tp_closed", order_id=order.id, symbol=symbol, reason=reason)
                else:
                    logger.warning("paper_sl_tp_close_failed", order_id=order.id, symbol=symbol)
            except Exception as e:
                logger.error("paper_sl_tp_exception", order_id=order.id, error=str(e))

        return closed

    def _persist_decision(self, db: Session, decision, symbol: str):
        """Save every orchestrator decision to DecisionLog for the AI Agents dashboard."""
        try:
            # Serialize agent_signals (AgentSignal objects -> dicts)
            signals_dict = {}
            if decision.agent_signals:
                for name, sig in decision.agent_signals.items():
                    if hasattr(sig, 'dict'):
                        signals_dict[name] = {
                            "signal": sig.signal,
                            "confidence": sig.confidence,
                            "reasoning": (sig.reasoning or "")[:300]
                        }
                    elif isinstance(sig, dict):
                        signals_dict[name] = sig

            log = DecisionLog(
                symbol=symbol,
                action=decision.action,
                confidence=decision.confidence,
                consensus_score=decision.consensus_score,
                market_regime=getattr(decision, 'market_regime', None),
                reasoning=(decision.reasoning or "")[:1000],
                agent_signals=signals_dict,
                state_vector=getattr(decision, 'state_vector', None)
            )
            db.add(log)

            db.commit()
            logger.info("decision_persisted", action=decision.action, symbol=symbol)
        except Exception as e:
            logger.error("decision_persist_failed", error=str(e))
            db.rollback()
    async def _get_portfolio_state(self, db: Session, exchange: ExchangeService, risk_state: RiskState) -> PortfolioState:
        """Fetch actual portfolio data from exchange (if Live) or DB (if Paper). Raises on failure."""
        from app.schemas.portfolio import Position, PortfolioState
        from app.models.order import Order
        from datetime import datetime, time, timezone, timedelta

        is_paper = not risk_state.is_live_enabled
        active_positions = []

        if risk_state.is_live_enabled:
            # 1. Fetch positions from exchange (LIVE)
            try:
                raw_positions = await exchange.exchange.fetch_positions()
                for p in raw_positions:
                    contracts = float(p.get("contracts", 0))
                    if contracts > 0:
                        active_positions.append(Position(
                            symbol=p.get("symbol", ""),
                            side="LONG" if p.get("side", "").lower() == "long" else "SHORT",
                            size=contracts,
                            entry_price=float(p.get("entryPrice", 0.0)),
                            current_price=float(p.get("markPrice", 0.0)),
                            unrealized_pnl=float(p.get("unrealizedPnl", 0.0)),
                            leverage=int(p.get("leverage", 1))
                        ))
            except Exception as e:
                logger.error("fetch_live_positions_failed", error=str(e))
                # Fallback to DB if exchange is down? No, better fail or return empty for safety
        else:
            # 1. Fetch positions from DB (PAPER)
            db_positions = db.query(Order).filter(
                Order.is_paper == True,
                Order.status == "FILLED",
                Order.closed_at == None
            ).all()
            
            ticker_cache = {}
            for op in db_positions:
                current_price = op.average_filled_price
                try:
                    if op.symbol not in ticker_cache:
                        ticker_cache[op.symbol] = await exchange.get_ticker(op.symbol)
                    ticker = ticker_cache[op.symbol]
                    current_price = float(ticker.get("last", current_price))
                except Exception as te:
                    logger.warning("ticker_fetch_failed_in_portfolio_state", symbol=op.symbol, error=str(te))
                    pass
                
                # Calculate simulated unrealized PnL
                if op.side == "BUY":
                    pnl = (current_price - op.average_filled_price) * op.requested_amount * op.leverage
                else:
                    pnl = (op.average_filled_price - current_price) * op.requested_amount * op.leverage
                
                active_positions.append(Position(
                    symbol=op.symbol,
                    side=op.side,
                    size=op.requested_amount,
                    entry_price=op.average_filled_price,
                    current_price=current_price,
                    unrealized_pnl=pnl,
                    leverage=op.leverage
                ))

        equity = risk_state.current_equity or 0.0
        if equity <= 0:
            raise ValueError("current_equity is zero or unset — balance sync required before trading")

        # 2. Calculate Daily PnL from DB (filtered by mode)
        today_start = datetime.combine(datetime.now(timezone.utc).date(), time.min).replace(tzinfo=timezone.utc)
        today_orders = db.query(Order).filter(
            Order.closed_at >= today_start, 
            Order.status == "CLOSED",
            Order.is_paper == is_paper
        ).all()
        daily_pnl = sum(o.pnl_usd or 0.0 for o in today_orders)
        daily_pnl_pct = (daily_pnl / equity * 100) if equity > 0 else 0.0

        # 3. Calculate Weekly PnL from DB (filtered by mode)
        week_start = datetime.now(timezone.utc) - timedelta(days=7)
        week_orders = db.query(Order).filter(
            Order.closed_at >= week_start, 
            Order.status == "CLOSED",
            Order.is_paper == is_paper
        ).all()
        weekly_pnl = sum(o.pnl_usd or 0.0 for o in week_orders)
        weekly_pnl_pct = (weekly_pnl / equity * 100) if equity > 0 else 0.0

        # 4. Calculate Drawdown
        peak = risk_state.equity_peak or equity or 1.0
        drawdown_pct = ((peak - equity) / peak * 100) if peak > 0 else 0.0

        # 5. Calculate available margin
        committed_notional = sum(p.entry_price * p.size for p in active_positions)
        available_margin = max(0.0, equity - committed_notional)

        return PortfolioState(
            total_balance=equity,
            total_equity=equity,
            available_margin=available_margin,
            open_positions=active_positions,
            daily_pnl_pct=round(daily_pnl_pct, 4),
            weekly_pnl_pct=round(weekly_pnl_pct, 4),
            max_drawdown_pct=round(drawdown_pct, 4)
        )


# Singleton instance
bot_runner = BotRunner()
