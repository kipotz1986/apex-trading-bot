"""
Master Orchestrator Agent.

Mengkoordinasikan seluruh agen analis, menjalankan Consensus Engine,
dan memvalidasi risiko untuk menghasilkan keputusan trading final.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from app.core.ai_provider import AIProvider
from app.core.logging import get_logger
from app.api.websocket import broadcast_updates
from app.agents.technical import TechnicalAnalystAgent
from app.agents.fundamental import FundamentalAnalystAgent
from app.agents.sentiment import SentimentAnalystAgent
from app.agents.risk_manager import RiskManagerAgent
from app.schemas.agent_signal import AgentSignal
from app.schemas.trade_decision import TradeDecision
from app.schemas.portfolio import PortfolioState, RiskDecision
from app.utils.prompts import get_prompt
from app.services.regime_detector import RegimeDetector
from app.services.regime_strategy import RegimeStrategy
from app.services.agent_scorer import AgentScorer
from app.services.execution import ExecutionEngine
from app.services.pre_trade_validator import PreTradeValidator
from app.services.learning.state_space import StateSpace
from app.services.learning.pattern_memory import PatternMemory
from app.services.mode_profile import get_active_profile, DEFAULT_PROFILE_SLUG, MODE_PROFILES
from app.models.system_settings import SystemSettings
from app.models.order import Order

logger = get_logger(__name__)


# ATR-based SL/TP multipliers per profile. Tuned to give a favourable R:R
# (winners on average bigger than losers) so the strategy survives a
# 35-45% win rate. Without these the bot opens trades with NO exit plan,
# which is the dominant cause of profit factor < 1.
PROFILE_SL_TP: Dict[str, Dict[str, Any]] = {
    "conservative":    {"sl_mult": 1.5, "tp_mults": [1.5, 3.0]},
    "balanced":        {"sl_mult": 2.0, "tp_mults": [2.0, 4.0, 6.0]},
    "aggressive":      {"sl_mult": 2.0, "tp_mults": [3.0, 5.0, 8.0]},
    "very_aggressive": {"sl_mult": 2.5, "tp_mults": [3.0, 6.0, 10.0]},
    "yolo":            {"sl_mult": 3.0, "tp_mults": [4.0, 8.0, 15.0]},
}
# Fallback ATR if technical agent didn't compute one: 2% of entry price.
ATR_FALLBACK_PCT = 0.02


class MasterOrchestrator:
    """Konduktor utama sistem multi-agent APEX."""

    def __init__(
        self,
        ai_provider: AIProvider,
        technical_agent: TechnicalAnalystAgent,
        fundamental_agent: FundamentalAnalystAgent,
        sentiment_agent: SentimentAnalystAgent,
        risk_manager: RiskManagerAgent,
        consensus_engine: Any,
        regime_detector: RegimeDetector,
        regime_strategy: RegimeStrategy,
        agent_scorer: AgentScorer,
        execution_engine: ExecutionEngine,
        pre_trade_validator: PreTradeValidator,
        state_space: StateSpace,
        pattern_memory: PatternMemory,
        rl_model: Any = None,
        db: Session = None
    ):
        self.db = db
        self.ai = ai_provider
        self.technical = technical_agent
        self.fundamental = fundamental_agent
        self.sentiment = sentiment_agent
        self.risk_manager = risk_manager
        self.consensus = consensus_engine
        self.regime_detector = regime_detector
        self.regime_strategy = regime_strategy
        self.agent_scorer = agent_scorer
        self.executor = execution_engine
        self.validator = pre_trade_validator
        self.state_space = state_space
        self.pattern_memory = pattern_memory
        self.rl_model = rl_model
        
        # Load prompt untuk Judge (Debate Protocol)
        try:
            self.judge_prompt = get_prompt("master_orchestrator_judge")
        except FileNotFoundError:
            # Fallback jika belum ada (akan dibuat di T-5.3)
            self.judge_prompt = "You are a senior trading strategist arbitrating conflicting signals."

    def _extract_atr(self, agent_signals: Dict[str, AgentSignal]) -> Optional[float]:
        """Pull ATR from technical agent's per-TF indicators. Prefers 1h, falls back to any available TF."""
        tech = agent_signals.get("technical") if agent_signals else None
        if not tech or not getattr(tech, "metadata", None):
            return None
        indicators = tech.metadata.get("indicators") if isinstance(tech.metadata, dict) else None
        if not indicators or not isinstance(indicators, dict):
            return None
        for tf in ("1h", "4h", "15m", "5m", "1m"):
            tf_ind = indicators.get(tf)
            if isinstance(tf_ind, dict) and tf_ind.get("atr"):
                try:
                    return float(tf_ind["atr"])
                except (TypeError, ValueError):
                    continue
        # last-resort: any timeframe with an ATR
        for tf_ind in indicators.values():
            if isinstance(tf_ind, dict) and tf_ind.get("atr"):
                try:
                    return float(tf_ind["atr"])
                except (TypeError, ValueError):
                    continue
        return None

    def _compute_atr_sl_tp(
        self,
        side: str,
        entry_price: float,
        agent_signals: Dict[str, AgentSignal],
        profile_slug: str,
    ) -> Dict[str, Any]:
        """
        Build default ATR-based stop_loss + take_profit ladder, profile-aware.
        Returns {"stop_loss": float, "take_profit": [float, ...]}.
        Used whenever upstream (debate protocol) didn't already provide them — which
        is the majority of trades.
        """
        if entry_price <= 0 or side not in ("BUY", "SELL"):
            return {"stop_loss": None, "take_profit": []}

        atr = self._extract_atr(agent_signals)
        if atr is None or atr <= 0:
            atr = entry_price * ATR_FALLBACK_PCT

        mults = PROFILE_SL_TP.get(profile_slug, PROFILE_SL_TP["balanced"])
        sl_distance = atr * float(mults["sl_mult"])
        tp_distances = [atr * float(m) for m in mults["tp_mults"]]

        # Price precision: 2 decimals for spot-priced majors; fine enough for SL/TP triggers.
        if side == "BUY":
            sl = entry_price - sl_distance
            tps = [entry_price + d for d in tp_distances]
        else:  # SELL
            sl = entry_price + sl_distance
            tps = [entry_price - d for d in tp_distances]

        # Guard against negative / zero TPs (e.g. tiny entry price with huge ATR)
        tps = [round(t, 4) for t in tps if t > 0]
        sl = round(sl, 4) if sl > 0 else None

        return {"stop_loss": sl, "take_profit": tps}

    async def decide(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        portfolio: PortfolioState,
    ) -> TradeDecision:
        """
        Alur utama pengambilan keputusan.
        """
        try:
            # 0. Global Circuit Breaker Check (Emergency Stop)
            is_triggered, cb_reason = await self.validator.circuit_breaker.check_all(portfolio.total_equity)
            if is_triggered and "Bot is stopped" in cb_reason:
                logger.warning("orchestrator_blocked_by_circuit_breaker", reason=cb_reason)
                return TradeDecision(
                    symbol=symbol, action="HOLD", confidence=0.0, consensus_score=0.0,
                    reasoning=f"SYSTEM BLOCKED: {cb_reason}", agent_signals={}, market_regime="unknown"
                )

            # 0. Detect Market Regime
            candles_dict = market_data.get("candles", {})
            # Use 1h for regime detection, or fallback to any available timeframe
            regime_candles = candles_dict.get("1h") or (next(iter(candles_dict.values()), []) if candles_dict else [])
            
            # Convert Pydantic models to dicts for the detector (which uses pandas)
            regime_candles_raw = [c.dict() for c in regime_candles] if regime_candles and hasattr(regime_candles[0], 'dict') else regime_candles
            regime_data = self.regime_detector.detect(regime_candles_raw)
            
            # 0.5. Check for Advanced Reasoning
            advanced_enabled = SystemSettings.get_value(self.db, "advanced_reasoning_enabled", "false") == "true"
            is_complex_regime = regime_data.get("regime") in ["high_volatility", "sideways", "unknown"]
            use_advanced = advanced_enabled and is_complex_regime
            
            if use_advanced:
                logger.info("advanced_reasoning_activated", regime=regime_data.get("regime"))
            
            await broadcast_updates("bot_progress", {"step": "analyzing_agents", "symbol": symbol})

            # 1. Kumpulkan sinyal dari analis secara paralel
            # Catatan: Risk Manager dieksekusi terakhir setelah ada target trade
            tasks = [
                self.technical.analyze(symbol, candles_dict, advanced=use_advanced),
                self.fundamental.analyze(
                    symbol, 
                    market_data.get("news", []), 
                    market_data.get("onchain_summary"),
                    market_data.get("onchain_stats"),
                    advanced=use_advanced
                ),
                self.sentiment.analyze(
                    symbol, 
                    market_data.get("composite_sentiment"),
                    market_data.get("exchange_sentiment", {}),
                    advanced=use_advanced
                )
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            agent_signals: Dict[str, AgentSignal] = {}
            agent_names = ["technical", "fundamental", "sentiment"]
            
            for name, res in zip(agent_names, results):
                if isinstance(res, Exception):
                    logger.error(f"agent_{name}_failed", error=str(res))
                    # Graceful degradation: isi dengan NEUTRAL
                    agent_signals[name] = AgentSignal(
                        agent_name=name,
                        symbol=symbol,
                        signal="NEUTRAL",
                        confidence=0.0,
                        reasoning=f"Agent error: {str(res)}"
                    )
                else:
                    agent_signals[name] = res

            # 2. Get dynamic weights and calculate consensus
            dynamic_weights = self.agent_scorer.get_weights()
            self.consensus.agent_weights = dynamic_weights # Inject weights
            
            # Fetch thresholds from DB
            threshold_strong = float(SystemSettings.get_value(self.db, "consensus_threshold_strong", 0.7))
            threshold_moderate = float(SystemSettings.get_value(self.db, "consensus_threshold_moderate", 0.4))
            
            await broadcast_updates("bot_progress", {"step": "calculating_consensus", "symbol": symbol})
            consensus_result = self.consensus.calculate(agent_signals, custom_thresholds={
                "strong": threshold_strong,
                "moderate": threshold_moderate
            })
            
            # 3. Debate Protocol (T-5.3) jika ada konflik atau skor WEAK
            if consensus_result.get("has_conflict") or (threshold_moderate <= abs(consensus_result.get("score", 0)) < threshold_strong):
                consensus_result = await self._run_debate_protocol(symbol, agent_signals, consensus_result, advanced=use_advanced)

            # Sizing — fall back to the ACTIVE profile's max_position_size rather than a
            # hardcoded aggressive 20%, so Conservative users don't get over-sized trades.
            try:
                active_profile = get_active_profile(self.db) if self.db is not None else MODE_PROFILES[DEFAULT_PROFILE_SLUG]
            except Exception:
                active_profile = MODE_PROFILES[DEFAULT_PROFILE_SLUG]
            profile_params = active_profile.get("params", {})
            profile_max_pos = profile_params.get("max_position_size", "20.0")
            profile_max_lev = int(profile_params.get("max_leverage", "15"))

            base_risk_pct = float(SystemSettings.get_value(self.db, "max_position_size", profile_max_pos)) / 100.0

            # Confidence-weighted sizing: scale proposed size by consensus confidence so
            # weak-conviction trades take smaller positions than high-conviction ones.
            # Floor at 0.3 so trades just above the entry threshold still get meaningful size.
            conf = float(consensus_result.get("confidence", 0.0))
            size_multiplier = min(max(conf, 0.3), 1.0)
            consensus_result["proposed_size"] = max(
                portfolio.total_equity * base_risk_pct * size_multiplier,
                10.0,
            )  # minimum $10

            # Seed leverage from the active profile so it isn't stuck at 1× later when
            # consensus_result has no leverage field. Risk manager will cap it per-trade.
            consensus_result.setdefault("leverage", profile_max_lev)

            # Apply Regime Strategy parameters on final consensus (after debate).
            # Pass user_threshold (moderate) so regime floor respects user settings.
            consensus_result = self.regime_strategy.adjust_decision(
                consensus_result, regime_data, user_threshold=threshold_moderate
            )

            # 3.5 Pattern Memory & RL Boost (Self-Learning)
            state_vec = self.state_space.build_vector(market_data, portfolio, agent_signals, symbol=symbol)
            
            # RL Model Prediction
            if self.rl_model:
                try:
                    # 0=HOLD, 1=LONG, 2=SHORT
                    rl_action, _states = self.rl_model.predict(state_vec, deterministic=True)
                    rl_map = {0: "HOLD", 1: "EXECUTE_LONG", 2: "EXECUTE_SHORT"}
                    rl_signal = rl_map.get(int(rl_action), "HOLD")
                    
                    if rl_signal == consensus_result["action"] and rl_signal != "HOLD":
                        consensus_result["confidence"] += 0.15  # stronger boost when RL agrees
                        consensus_result["reasoning"] += f" | RL Model Sync: {rl_signal} confirmed."
                    elif rl_signal != "HOLD" and consensus_result["action"] != "HOLD" and rl_signal != consensus_result["action"]:
                        consensus_result["confidence"] -= 0.1  # softer penalty in aggressive mode
                        consensus_result["reasoning"] += f" | RL Model Conflict: Neural net suggests {rl_signal}."
                except Exception as e:
                    logger.warning("rl_prediction_failed", error=str(e))

            # Pattern Memory Experience — filter by symbol so BTC patterns don't taint ETH/SOL
            experience = self.pattern_memory.get_market_experience(state_vec.tolist(), symbol=symbol)
            
            if experience["sample_size"] >= 3:
                wr = experience["win_rate"]
                if wr > 0.6:  # lowered threshold from 70% to 60% — easier boost
                    consensus_result["confidence"] += 0.15
                    consensus_result["reasoning"] += f" | Pattern Memory Boost: {wr:.0%} WR in similar conditions."
                elif wr < 0.25:  # only penalize on truly bad track record
                    consensus_result["confidence"] -= 0.10
                    consensus_result["reasoning"] += f" | Pattern Memory Warning: Only {wr:.0%} WR in similar conditions."

            # Clamp confidence to [0.0, 1.0] after all RL/pattern memory adjustments
            consensus_result["confidence"] = min(max(consensus_result["confidence"], 0.0), 1.0)

            # 4. Final Risk Validation (Veto Power)
            # Konversi consensus action ke side
            side = "BUY" if "LONG" in consensus_result["action"] else "SELL" if "SHORT" in consensus_result["action"] else "NEUTRAL"
            
            # --- POSITIVE REVERSAL / COURAGE TO CLOSE LOGIC ---
            # Collect ALL open positions for this symbol (not just the first one)
            open_positions_for_symbol = [p for p in portfolio.open_positions if p.symbol == symbol]
            
            if open_positions_for_symbol:
                should_close = False
                close_reason = ""
                # Use the dominant side (most positions) for reversal logic
                long_positions = [p for p in open_positions_for_symbol if p.side in ("LONG", "BUY")]
                short_positions = [p for p in open_positions_for_symbol if p.side in ("SHORT", "SELL")]
                dominant_side = "LONG" if len(long_positions) >= len(short_positions) else "SHORT"
                positions_to_close = long_positions if dominant_side == "LONG" else short_positions
                
                # 1. Direct Reversal (Signal is completely opposite)
                if (dominant_side == "LONG" and side == "SELL") or (dominant_side == "SHORT" and side == "BUY"):
                    should_close = True
                    close_reason = f"Trend Reversal (New Signal: {side}, Open: {dominant_side}, Positions: {len(positions_to_close)})"
                
                # 2. Weakening Momentum (Signal is HOLD, but score leans against the open position).
                # NOTE: when consensus action is HOLD, the score is bounded by ±threshold_moderate,
                # so the weakening threshold MUST be smaller than threshold_moderate or the branch
                # is unreachable. Use 75% of the entry threshold as the early-warning floor.
                elif side == "NEUTRAL":
                    score = consensus_result.get("score", 0.0)
                    weakening_threshold = threshold_moderate * 0.75

                    if dominant_side == "LONG" and score < -weakening_threshold:
                        should_close = True
                        close_reason = f"Momentum Shift Bearish (Score: {score:.2f} < -{weakening_threshold:.2f}, Positions: {len(positions_to_close)})"
                    elif dominant_side == "SHORT" and score > weakening_threshold:
                        should_close = True
                        close_reason = f"Momentum Shift Bullish (Score: {score:.2f} > {weakening_threshold:.2f}, Positions: {len(positions_to_close)})"
                
                # --- PnL-AWARE CLOSE GUARD ---
                # Don't panic-close positions that are in a minor loss. Require a much
                # stronger signal (0.9x threshold_moderate) for losing positions within
                # tolerance so they have room to recover.
                if should_close and side == "NEUTRAL":
                    total_unrealized = sum(p.unrealized_pnl for p in positions_to_close)
                    loss_tolerance_pct = float(SystemSettings.get_value(self.db, "loss_tolerance_pct", "5.0"))
                    loss_pct = (total_unrealized / portfolio.total_equity * 100) if portfolio.total_equity > 0 else 0

                    if total_unrealized < 0 and loss_pct > -loss_tolerance_pct:
                        # Position is in loss but within tolerance — require STRONGER signal
                        strict_threshold = threshold_moderate * 0.9
                        score = consensus_result.get("score", 0.0)
                        if dominant_side == "LONG" and score >= -strict_threshold:
                            should_close = False
                        elif dominant_side == "SHORT" and score <= strict_threshold:
                            should_close = False
                        if not should_close:
                            logger.info("loss_tolerance_hold", symbol=symbol,
                                        loss_pct=f"{loss_pct:.2f}%", score=score,
                                        strict_threshold=strict_threshold)

                # --- MINIMUM HOLD TIME GUARD ---
                # Don't close recently-opened positions on momentum shift alone.
                # Direct reversals (BUY→SELL) are always allowed regardless of hold time.
                if should_close and side == "NEUTRAL":
                    min_hold_minutes = int(SystemSettings.get_value(self.db, "min_hold_time_minutes", "30"))
                    newest_order = self.db.query(Order).filter(
                        Order.symbol == symbol,
                        Order.status.in_(["OPEN", "FILLED"]),
                        Order.closed_at == None
                    ).order_by(Order.created_at.desc()).first()

                    if newest_order and newest_order.created_at:
                        order_ts = newest_order.created_at
                        if order_ts.tzinfo is None:
                            order_ts = order_ts.replace(tzinfo=timezone.utc)
                        age_minutes = (datetime.now(timezone.utc) - order_ts).total_seconds() / 60
                        if age_minutes < min_hold_minutes:
                            should_close = False
                            logger.info("min_hold_time_guard", symbol=symbol,
                                        age_minutes=round(age_minutes), min=min_hold_minutes)

                if should_close:
                    logger.info("orchestrator_closing_positions", symbol=symbol, reason=close_reason, count=len(positions_to_close))
                    await broadcast_updates("bot_progress", {"step": "finalizing_decision", "symbol": symbol})
                    
                    # Close ALL matching positions, not just the first one
                    closed_count = 0
                    for pos in positions_to_close:
                        closed_ok = await self.executor.close_position(symbol, pos.side, pos.size)
                        if closed_ok:
                            closed_count += 1
                        else:
                            logger.warning("failed_to_close_one_position", symbol=symbol, side=pos.side, size=pos.size)
                    
                    if closed_count > 0:
                        if side == "NEUTRAL":
                            return TradeDecision(
                                symbol=symbol, action="HOLD",
                                confidence=consensus_result["confidence"], consensus_score=consensus_result["score"],
                                reasoning=f"Proactive Closure: {closed_count}/{len(positions_to_close)} positions closed due to {close_reason}.",
                                agent_signals=agent_signals, market_regime=regime_data["regime"],
                                state_vector=state_vec.tolist()
                            )
                        consensus_result["reasoning"] += f" | Proactive Closure: {closed_count} prior {dominant_side} positions closed ({close_reason})."
                    else:
                        logger.error("failed_to_close_any_position", symbol=symbol)
                        return TradeDecision(
                            symbol=symbol, action="HOLD", confidence=0.0, consensus_score=consensus_result["score"],
                            reasoning=f"BLOCKED: Failed to close existing {dominant_side} positions.",
                            agent_signals=agent_signals, market_regime=regime_data["regime"], state_vector=state_vec.tolist()
                        )
            
            # --- EXPOSURE RELIEF: Close stale positions when exposure cap is saturated ---
            # If total exposure exceeds the profile cap and no trade can go through,
            # proactively close the oldest/smallest position for this symbol to free margin.
            if side == "NEUTRAL" and open_positions_for_symbol:
                current_exposure = sum(p.size * p.current_price for p in portfolio.open_positions)
                exposure_pct = (current_exposure / portfolio.total_equity * 100) if portfolio.total_equity > 0 else 0
                max_exposure = float(SystemSettings.get_value(self.db, "max_total_exposure", "80.0"))
                
                if exposure_pct > max_exposure:
                    # Close the smallest/oldest position to free capacity
                    # Prefer closing profitable positions first (take profit to free margin)
                    # so losing positions have room to recover.
                    profitable = [p for p in open_positions_for_symbol if p.unrealized_pnl > 0]
                    if profitable:
                        stale_pos = min(profitable, key=lambda p: p.unrealized_pnl)
                    else:
                        stale_pos = min(open_positions_for_symbol, key=lambda p: p.size * p.current_price)
                    stale_notional = stale_pos.size * stale_pos.current_price
                    logger.info("exposure_relief_triggered", symbol=symbol, exposure_pct=round(exposure_pct, 1), closing_notional=round(stale_notional, 2))
                    
                    closed_ok = await self.executor.close_position(symbol, stale_pos.side, stale_pos.size)
                    if closed_ok:
                        return TradeDecision(
                            symbol=symbol, action="HOLD",
                            confidence=consensus_result["confidence"], consensus_score=consensus_result["score"],
                            reasoning=f"Exposure Relief: Closed smallest {stale_pos.side} position (${stale_notional:.0f}) to free margin. Exposure was {exposure_pct:.1f}% > {max_exposure}% cap.",
                            agent_signals=agent_signals, market_regime=regime_data["regime"],
                            state_vector=state_vec.tolist()
                        )

            if side == "NEUTRAL":
                return TradeDecision(
                    symbol=symbol,
                    action="HOLD",
                    confidence=consensus_result["confidence"],
                    consensus_score=consensus_result["score"],
                    reasoning=consensus_result["reasoning"],
                    agent_signals=agent_signals,
                    market_regime=regime_data["regime"],
                    state_vector=state_vec.tolist()
                )
            
            # Get current price from candles for validation
            current_price = 0.0
            if regime_candles:
                last_candle = regime_candles[-1]
                current_price = float(last_candle.close if hasattr(last_candle, 'close') else last_candle.get('close', 0.0))
            
            if current_price <= 0.0:
                try:
                    ticker = await self.executor.exchange.get_ticker(symbol)
                    current_price = float(ticker.get("last", 0.0))
                except Exception as e:
                    logger.warning("failed_to_fetch_fallback_ticker", symbol=symbol, error=str(e))

            await broadcast_updates("bot_progress", {"step": "evaluating_risk", "symbol": symbol})
            risk_res = await self.risk_manager.analyze(
                symbol=symbol,
                side=side,
                trade_size_usd=consensus_result["proposed_size"],
                portfolio=portfolio,
                market_volatility=regime_data["regime"],
                db=self.db,
                advanced=use_advanced
            )
            
            # Create decision object
            # Leverage: take the smaller of profile-seeded consensus leverage and the
            # risk manager's per-trade max — both already respect the active profile.
            desired_leverage = int(consensus_result.get("leverage", risk_res.max_leverage))
            final_leverage = max(1, min(desired_leverage, int(risk_res.max_leverage)))

            # MANDATORY SL/TP. Upstream debate protocol may have set these; if not,
            # synthesize a profile-aware ATR ladder so no trade opens without an exit
            # plan. This was the #1 cause of profit factor < 1 in prior runs.
            sl_from_upstream = consensus_result.get("stop_loss")
            tp_from_upstream = consensus_result.get("take_profit") or []
            if not sl_from_upstream or not tp_from_upstream:
                default_levels = self._compute_atr_sl_tp(
                    side=side,
                    entry_price=current_price,
                    agent_signals=agent_signals,
                    profile_slug=active_profile.get("slug", DEFAULT_PROFILE_SLUG),
                )
                if not sl_from_upstream and default_levels["stop_loss"]:
                    sl_from_upstream = default_levels["stop_loss"]
                if not tp_from_upstream and default_levels["take_profit"]:
                    tp_from_upstream = default_levels["take_profit"]
                logger.info(
                    "atr_default_sl_tp_applied",
                    symbol=symbol, side=side, entry=current_price,
                    sl=sl_from_upstream, tp=tp_from_upstream,
                    profile=active_profile.get("slug"),
                )

            decision = TradeDecision(
                symbol=symbol,
                action=consensus_result["action"],
                confidence=consensus_result["confidence"],
                consensus_score=consensus_result["score"],
                position_size_usd=risk_res.max_position_size_usd,
                leverage=final_leverage,
                stop_loss=sl_from_upstream,
                take_profit=tp_from_upstream,
                reasoning=consensus_result["reasoning"],
                agent_signals=agent_signals,
                market_regime=regime_data["regime"],
                state_vector=state_vec.tolist()
            )

            if risk_res.decision == "REJECT":
                decision.action = "HOLD"
                decision.reasoning = f"REJECTED BY RISK MANAGER: {risk_res.reasoning}"
                return decision

            if risk_res.decision == "REDUCE_SIZE":
                decision.position_size_usd = risk_res.max_position_size_usd
                decision.reasoning += f" | RISK MANAGER: Size reduced to ${risk_res.max_position_size_usd:.2f} — {risk_res.reasoning}"
                logger.info("position_size_reduced_by_risk_manager", symbol=symbol, new_size=risk_res.max_position_size_usd)

            # 5. Pre-Trade Validation Gateway
            is_valid, reject_reason = await self.validator.validate(
                decision=decision,
                portfolio=portfolio,
                market_price=current_price
            )

            if not is_valid:
                decision.action = "HOLD"
                decision.reasoning = f"PRE-TRADE VALIDATION FAILED: {reject_reason}"
                return decision

            await broadcast_updates("bot_progress", {"step": "finalizing_decision", "symbol": symbol})
            # 6. EXECUTE!
            logger.info("executing_trade", symbol=symbol, side=side, amount=decision.position_size_usd)

            # Telegram alert — fires for EVERY execution decision that passes risk + validation
            if self.executor and self.executor.telegram:
                signals_for_tg = {
                    name: {
                        "signal": sig.signal,
                        "confidence": sig.confidence,
                    } for name, sig in agent_signals.items()
                }
                asyncio.create_task(self.executor.telegram.send_decision_alert(
                    symbol=symbol,
                    action=decision.action,
                    confidence=decision.confidence,
                    consensus_score=decision.consensus_score,
                    position_size_usd=decision.position_size_usd or 0.0,
                    leverage=decision.leverage or 1,
                    regime=regime_data.get("regime", "unknown"),
                    reasoning=decision.reasoning or "",
                    agent_signals=signals_for_tg,
                ))

            # Convert USD size to Asset Amount (Simplified: size / price)
            size_usd = decision.position_size_usd or 0.0
            asset_amount = size_usd / current_price if current_price > 0 else 0

            if asset_amount <= 0:
                decision.action = "HOLD"
                decision.reasoning = f"Calculated asset amount is zero (Size: ${size_usd}, Price: {current_price})."
                return decision

            res = await self.executor.open_position(
                symbol=symbol,
                side=side,
                amount=asset_amount,
                order_type="MARKET", # Default to market for auto-execution
                price=current_price, # FIXED: pass price for paper/live calculation
                leverage=decision.leverage,
                stop_loss=decision.stop_loss,
                take_profits=decision.take_profit,
                reasoning=decision.reasoning,
                state_vector=state_vec.tolist(),
                agent_signals={k: v.signal for k, v in agent_signals.items()}
            )

            if res:
                decision.reasoning += f" | EXECUTED ID: {res.exchange_order_id}"
            else:
                decision.action = "HOLD"
                decision.reasoning += " | EXECUTION FAILED AT EXCHANGE"

            return decision

        except Exception as e:
            logger.error("orchestrator_decision_failed", error=str(e))
            return TradeDecision(
                symbol=symbol,
                action="HOLD",
                confidence=0.0,
                consensus_score=0.0,
                reasoning=f"Critical error in Orchestrator: {str(e)}",
                agent_signals={},
                market_regime="unknown"
            )

    async def _run_debate_protocol(self, symbol: str, signals: Dict[str, AgentSignal], consensus: Dict[str, Any], advanced: bool = False) -> Dict[str, Any]:
        """
        Menjalankan AI Judge untuk menengahi konflik antar agen.
        """
        logger.info("debate_protocol_triggered", symbol=symbol)
        
        try:
            # Format signals for AI
            signals_data = {
                name: {
                    "signal": sig.signal,
                    "confidence": sig.confidence,
                    "reasoning": sig.reasoning
                } for name, sig in signals.items()
            }
            
            # Prepare data for judge
            data_str = json.dumps({
                "symbol": symbol,
                "agent_signals": signals_data,
                "current_consensus": {
                    "score": consensus["score"],
                    "action": consensus["action"]
                }
            }, indent=2)
            
            instruction = (
                "Review the conflicting analyst signals and provide a definitive decision. "
                "Explain which agent's logic is superior in this specific context."
            )

            response = await self.ai.analyze(
                system_prompt=self.judge_prompt,
                data=data_str,
                instruction=instruction,
                json_mode=True,
                agent_name="master_orchestrator",
                advanced=advanced
            )
            
            judge_res = json.loads(response.content)
            
            # Update consensus with judge decision
            updated_consensus = consensus.copy()
            updated_consensus.update({
                "action": judge_res.get("action", consensus["action"]),
                "confidence": judge_res.get("confidence", consensus["confidence"]),
                "reasoning": f"[JUDGE DECISION] {judge_res.get('reasoning', '')}",
                "arbitrated_by_judge": True
            })
            
            # Carry over numeric values if provided
            if "stop_loss" in judge_res: updated_consensus["stop_loss"] = judge_res["stop_loss"]
            if "take_profit" in judge_res: updated_consensus["take_profit"] = judge_res["take_profit"]
            
            logger.info("debate_resolved", action=updated_consensus["action"])
            return updated_consensus
            
        except Exception as e:
            logger.error("debate_protocol_failed", error=str(e))
            # Fallback to original consensus
            return consensus
