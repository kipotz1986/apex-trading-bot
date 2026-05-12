"""
Risk Manager Agent.

Bertanggung jawab untuk mengevaluasi trade request berdasarkan
aturan risiko portofolio dan kondisi pasar. Memiliki wewenang final
untuk menolak trade.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.system_settings import SystemSettings
from app.core.ai_provider import AIProvider
from app.core.logging import get_logger
from app.schemas.portfolio import PortfolioState, RiskDecision
from app.utils.prompts import get_prompt

logger = get_logger(__name__)

class RiskManagerAgent:
    """Agent yang mengelola risiko dan validasi trade."""

    AGENT_NAME = "risk_manager"

    # Very Aggressive defaults — fewer hard rejections, larger size/exposure tolerance
    MAX_POSITION_SIZE_PCT = 0.20  # 20% per posisi
    MAX_TOTAL_EXPOSURE_PCT = 0.80 # 80% total eksposur
    DAILY_LOSS_LIMIT_PCT = 12.0   # 12% daily loss tolerance
    MAX_DRAWDOWN_LIMIT_PCT = 30.0 # 30% max drawdown before emergency stop

    def __init__(self, ai_provider: AIProvider):
        self.ai = ai_provider
        self.system_prompt = get_prompt("risk_manager")

    def evaluate_hard_rules(
        self, 
        portfolio: PortfolioState, 
        trade_size_usd: float,
        daily_loss_limit: float,
        max_total_exposure: float,
        max_pos_pct: float
    ) -> Optional[RiskDecision]:
        """
        Evaluasi aturan risiko yang kaku (hard rules).
        """
        # 1. Check Daily Loss Limit (daily_loss_limit is positive %, e.g. 3.0; daily_pnl_pct is also %, e.g. -3.0)
        if portfolio.daily_pnl_pct <= -daily_loss_limit:
            return RiskDecision(
                decision="REJECT",
                max_position_size_usd=0.0,
                max_leverage=1,
                reasoning=f"Daily loss limit reached ({portfolio.daily_pnl_pct:.2f}%). Limit: {daily_loss_limit}%",
                risk_metrics={"daily_pnl_pct": portfolio.daily_pnl_pct}
            )

        # 2. Check Max Drawdown (max_drawdown_pct is positive %, e.g. 15.0)
        if portfolio.max_drawdown_pct >= self.MAX_DRAWDOWN_LIMIT_PCT:
            return RiskDecision(
                decision="REJECT",
                max_position_size_usd=0.0,
                max_leverage=1,
                reasoning=f"Max drawdown reached ({portfolio.max_drawdown_pct:.2f}%). Critical safety stop.",
                risk_metrics={"max_drawdown_pct": portfolio.max_drawdown_pct}
            )

        # 3. Check Max Position Size (Hard Cap) — only intervene on truly extreme sizing
        max_size_allowed = portfolio.total_equity * (max_pos_pct / 100)
        if trade_size_usd > max_size_allowed:
             if trade_size_usd > portfolio.total_equity * 0.50: # Extreme case raised from 20% to 50%
                 return RiskDecision(
                     decision="REDUCE_SIZE",
                     max_position_size_usd=max_size_allowed,
                     max_leverage=15,
                     reasoning=f"Trade size (${trade_size_usd}) is too large. Hard capped at {max_pos_pct}% equity.",
                     risk_metrics={"max_allowed": max_size_allowed}
                 )

        # 4. Check Total Exposure
        current_exposure = sum(p.size * p.current_price for p in portfolio.open_positions)
        new_total_exposure = current_exposure + trade_size_usd
        exposure_pct = new_total_exposure / portfolio.total_equity
        if exposure_pct > (max_total_exposure / 100):
            return RiskDecision(
                decision="REJECT",
                max_position_size_usd=0.0,
                max_leverage=1,
                reasoning=f"Max total exposure reached ({exposure_pct:.2%}). Limit is {max_total_exposure}%",
                risk_metrics={"current_exposure_pct": exposure_pct}
            )

        return None

    async def analyze(
        self,
        symbol: str,
        side: str, # "BUY" (Long) | "SELL" (Short)
        trade_size_usd: float,
        portfolio: PortfolioState,
        market_volatility: str = "normal", # low/normal/high
        db: Session = None
    ) -> RiskDecision:
        """
        Analisa risiko lengkap menggabungkan hard rules dan AI reasoning.
        """
        try:
            # Step 0: Get Dynamic Limits — aggressive defaults if DB has no override
            if db:
                daily_limit = float(SystemSettings.get_value(db, "daily_loss_limit", "12.0"))
                max_leverage = int(SystemSettings.get_value(db, "max_leverage", "15"))
                max_pos_pct = float(SystemSettings.get_value(db, "max_position_size", "20.0"))
                max_exposure = float(SystemSettings.get_value(db, "max_total_exposure", "80.0"))
            else:
                daily_limit = 12.0
                max_leverage = 15
                max_pos_pct = 20.0
                max_exposure = 80.0

            # Step 1: Validasi Hard Rules (Security Layer)
            hard_decision = self.evaluate_hard_rules(
                portfolio, 
                trade_size_usd,
                daily_limit,
                max_exposure,
                max_pos_pct
            )
            if hard_decision:
                logger.info("risk_hard_rule_triggered", decision=hard_decision.decision, reason=hard_decision.reasoning)
                return hard_decision

            # Step 2: AI Reasoning for soft rules (Correlation, Volatility, Sizing)
            data_str = f"Symbol: {symbol}\nAction: {side}\nProposed Size: ${trade_size_usd}\n"
            data_str += f"\nPortfolio Status:\n{portfolio.model_dump_json(indent=2)}\n"
            data_str += f"\nMarket Volatility: {market_volatility}\n"
            data_str += f"\nRisk Limits: Daily Loss {daily_limit}%, Max Pos {max_pos_pct}%, Max Leverage {max_leverage}x\n"

            instruction = (
                f"Evaluate the risk for {side} {symbol} with size ${trade_size_usd}. "
                f"Consider current open positions for correlation risk. "
                f"Decide if we should APPROVE, REJECT, or REDUCE_SIZE."
            )

            response = await self.ai.analyze(
                system_prompt=self.system_prompt,
                data=data_str,
                instruction=instruction,
                json_mode=True,
                agent_name=self.AGENT_NAME,
            )

            # Step 3: Parse response AI
            try:
                result = json.loads(response.content)
            except json.JSONDecodeError:
                logger.error("ai_json_decode_failed", content=response.content)
                # Fallback aman
                return RiskDecision(
                    decision="REJECT",
                    max_position_size_usd=0.0,
                    max_leverage=1,
                    reasoning="Gagal memproses respons AI Risk Manager.",
                )

            # Step 4: Ensure AI doesn't violate hard rules (Double check)
            final_size = result.get("max_position_size_usd", trade_size_usd)
            hard_cap = portfolio.total_equity * (max_pos_pct / 100)
            if final_size > hard_cap:
                final_size = hard_cap
                result["decision"] = "REDUCE_SIZE"
                result["reasoning"] += f" (Note: Size capped at {max_pos_pct}% equity by safety layer)"

            final_leverage = min(result.get("max_leverage", max_leverage), max_leverage)

            return RiskDecision(
                decision=result.get("decision", "REJECT"),
                max_position_size_usd=final_size,
                max_leverage=final_leverage,
                reasoning=result.get("reasoning", "No reasoning provided."),
                risk_metrics=result.get("risk_metrics", {})
            )

        except Exception as e:
            logger.error("risk_analysis_failed", error=str(e))
            return RiskDecision(
                decision="REJECT",
                max_position_size_usd=0.0,
                max_leverage=1,
                reasoning=f"Error dalam analisis risiko: {str(e)}",
            )
