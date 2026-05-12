"""
Master Orchestrator Agent.

Mengkoordinasikan seluruh agen analis, menjalankan Consensus Engine,
dan memvalidasi risiko untuk menghasilkan keputusan trading final.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from app.core.ai_provider import AIProvider
from app.core.logging import get_logger
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
from app.models.system_settings import SystemSettings

logger = get_logger(__name__)


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
            
            consensus_result = self.consensus.calculate(agent_signals, custom_thresholds={
                "strong": threshold_strong,
                "moderate": threshold_moderate
            })
            
            # 3. Debate Protocol (T-5.3) jika ada konflik atau skor WEAK
            if consensus_result.get("has_conflict") or (threshold_moderate <= abs(consensus_result.get("score", 0)) < threshold_strong):
                consensus_result = await self._run_debate_protocol(symbol, agent_signals, consensus_result, advanced=use_advanced)

            # Aggressive: default 20% per trade if no DB override
            base_risk_pct = float(SystemSettings.get_value(self.db, "max_position_size", "20.0")) / 100.0
            consensus_result["proposed_size"] = max(portfolio.total_equity * base_risk_pct, 10.0) # minimum $10

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

            risk_res = await self.risk_manager.analyze(
                symbol=symbol,
                side=side,
                trade_size_usd=consensus_result["proposed_size"],
                portfolio=portfolio,
                market_volatility=regime_data["regime"],
                db=self.db
            )
            
            # Create decision object
            decision = TradeDecision(
                symbol=symbol,
                action=consensus_result["action"],
                confidence=consensus_result["confidence"],
                consensus_score=consensus_result["score"],
                position_size_usd=risk_res.max_position_size_usd,
                leverage=min(consensus_result.get("leverage", 1), risk_res.max_leverage),
                stop_loss=consensus_result.get("stop_loss"),
                take_profit=consensus_result.get("take_profit", []),
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
