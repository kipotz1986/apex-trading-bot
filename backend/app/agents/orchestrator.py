"""
Master Orchestrator Agent.

Mengkoordinasikan seluruh agen analis, menjalankan Consensus Engine,
dan memvalidasi risiko untuk menghasilkan keputusan trading final.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from app.core.ai_provider import AIProvider
from app.core.logging import get_logger
from app.agents.technical import TechnicalAnalystAgent
from app.agents.fundamental import FundamentalAnalystAgent
from app.agents.sentiment import SentimentAnalystAgent
from app.agents.risk_manager import RiskManagerAgent
from app.agents.copy_trader import CopyTradingAgent
from app.schemas.agent_signal import AgentSignal
from app.schemas.trade_decision import TradeDecision
from app.schemas.portfolio import PortfolioState, RiskDecision
from app.utils.prompts import get_prompt
from app.services.regime_detector import RegimeDetector
from app.services.regime_strategy import RegimeStrategy
from app.services.agent_scorer import AgentScorer
from app.services.execution import ExecutionEngine
from app.services.pre_trade_validator import PreTradeValidator

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
        copy_trader: CopyTradingAgent,
        consensus_engine: Any,
        regime_detector: RegimeDetector,
        regime_strategy: RegimeStrategy,
        agent_scorer: AgentScorer,
        execution_engine: ExecutionEngine,
        pre_trade_validator: PreTradeValidator
    ):
        self.ai = ai_provider
        self.technical = technical_agent
        self.fundamental = fundamental_agent
        self.sentiment = sentiment_agent
        self.risk_manager = risk_manager
        self.copy_trader = copy_trader
        self.consensus = consensus_engine
        self.regime_detector = regime_detector
        self.regime_strategy = regime_strategy
        self.agent_scorer = agent_scorer
        self.executor = execution_engine
        self.validator = pre_trade_validator
        
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
            # 0. Detect Market Regime
            regime_data = self.regime_detector.detect(market_data.get("candles", []))
            
            # 1. Kumpulkan sinyal dari analis secara paralel
            # Catatan: Risk Manager dieksekusi terakhir setelah ada target trade
            tasks = [
                self.technical.analyze(symbol, market_data.get("candles", {})),
                self.fundamental.analyze(
                    symbol, 
                    market_data.get("news", []), 
                    market_data.get("onchain_summary"),
                    market_data.get("onchain_stats")
                ),
                self.sentiment.analyze(
                    symbol, 
                    market_data.get("composite_sentiment"),
                    market_data.get("exchange_sentiment", {})
                ),
                self.copy_trader.analyze(symbol)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            agent_signals: Dict[str, AgentSignal] = {}
            agent_names = ["technical", "fundamental", "sentiment", "copy_trader"]
            
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
            consensus_result = self.consensus.calculate(agent_signals)
            
            # 3. Debate Protocol (T-5.3) jika ada konflik atau skor WEAK
            if consensus_result.get("has_conflict") or (0.4 <= consensus_result.get("score", 0) < 0.7):
                consensus_result = await self._run_debate_protocol(symbol, agent_signals, consensus_result)

            # Apply Regime Strategy parameters on final consensus (after debate)
            consensus_result = self.regime_strategy.adjust_decision(consensus_result, regime_data)

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
                    market_regime=regime_data["regime"]
                )
            
            # Get current price from candles for validation
            current_price = market_data.get("candles", [])[-1].get("close") if market_data.get("candles") else 0.0

            risk_res = await self.risk_manager.analyze(
                symbol=symbol,
                side=side,
                trade_size_usd=consensus_result["proposed_size"],
                portfolio=portfolio,
                market_volatility=regime_data["regime"]
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
                market_regime=regime_data["regime"]
            )

            if risk_res.decision == "REJECT":
                decision.action = "HOLD"
                decision.reasoning = f"REJECTED BY RISK MANAGER: {risk_res.reasoning}"
                return decision

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
            
            # Convert USD size to Asset Amount (Simplified: size / price)
            asset_amount = decision.position_size_usd / current_price if current_price > 0 else 0
            
            if asset_amount <= 0:
                decision.action = "HOLD"
                decision.reasoning = "Calculated asset amount is zero."
                return decision

            res = await self.executor.open_position(
                symbol=symbol,
                side=side,
                amount=asset_amount,
                order_type="MARKET", # Default to market for auto-execution
                leverage=decision.leverage,
                stop_loss=decision.stop_loss,
                take_profits=decision.take_profit,
                reasoning=decision.reasoning
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
                agent_signals={}
            )

    async def _run_debate_protocol(self, symbol: str, signals: Dict[str, AgentSignal], consensus: Dict[str, Any]) -> Dict[str, Any]:
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
                json_mode=True
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
