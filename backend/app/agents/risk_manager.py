"""
Risk Manager Agent.

Bertanggung jawab untuk mengevaluasi trade request berdasarkan
aturan risiko portofolio dan kondisi pasar. AI selalu menjadi pengambil
keputusan utama; hard rules disajikan sebagai konteks dan hanya
men-override AI untuk pelanggaran fatal (daily loss limit, max drawdown).
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.system_settings import SystemSettings
from app.core.ai_provider import AIProvider
from app.core.logging import get_logger
from app.schemas.portfolio import PortfolioState, RiskDecision
from app.utils.prompts import get_prompt
from app.services.mode_profile import (
    MODE_PROFILES,
    DEFAULT_PROFILE_SLUG,
    get_active_profile,
    get_profile,
)


# Per-profile behavioral bias the AI receives as a system-level instruction.
# Order matches risk_level ascending.
PROFILE_BIAS: Dict[str, Dict[str, Any]] = {
    "conservative": {
        "stance": "VERY CAUTIOUS",
        "default_decision": "REJECT when in doubt",
        "approve_bar": "Approve only when every signal aligns and size is small.",
        "size_bias": "Prefer REDUCE_SIZE down to 50% of the proposed size unless setup is pristine.",
        "leverage_bias": "Default to 1x–2x even when higher is allowed.",
    },
    "balanced": {
        "stance": "MEASURED",
        "default_decision": "Weigh approve vs reject based on evidence",
        "approve_bar": "Approve when most signals align and risk metrics are comfortable.",
        "size_bias": "Use proposed size when within soft cap; REDUCE_SIZE if close to caps.",
        "leverage_bias": "Use 3x–5x typical; cap matches profile.",
    },
    "aggressive": {
        "stance": "OPPORTUNISTIC",
        "default_decision": "Lean APPROVE when no hard rule is breached",
        "approve_bar": "Approve unless there's a clear, concrete risk signal.",
        "size_bias": "Use proposed size; only REDUCE_SIZE when soft cap is breached.",
        "leverage_bias": "Use up to profile max comfortably.",
    },
    "very_aggressive": {
        "stance": "STRONGLY BIASED TO APPROVE",
        "default_decision": "APPROVE by default",
        "approve_bar": "Reject only when a hard rule is clearly breached or correlation is extreme.",
        "size_bias": "Honor proposed size; REDUCE_SIZE only when extreme cap (>50% equity) is hit.",
        "leverage_bias": "Use profile max leverage freely.",
    },
    "yolo": {
        "stance": "MAXIMUM SEND",
        "default_decision": "APPROVE almost unconditionally",
        "approve_bar": "Reject only if the trade would literally violate a critical override (daily loss / max drawdown already pre-handled).",
        "size_bias": "Approve full proposed size; REDUCE_SIZE only on extreme cap breach.",
        "leverage_bias": "Max leverage is fine.",
    },
}

logger = get_logger(__name__)

class RiskManagerAgent:
    """Agent yang mengelola risiko dan validasi trade via AI reasoning."""

    AGENT_NAME = "risk_manager"

    # Very Aggressive defaults — fewer hard rejections, larger size/exposure tolerance
    MAX_POSITION_SIZE_PCT = 0.20  # 20% per posisi
    MAX_TOTAL_EXPOSURE_PCT = 0.80 # 80% total eksposur
    DAILY_LOSS_LIMIT_PCT = 12.0   # 12% daily loss tolerance
    MAX_DRAWDOWN_LIMIT_PCT = 30.0 # 30% max drawdown before emergency stop

    def __init__(self, ai_provider: AIProvider):
        self.ai = ai_provider
        self.base_prompt = get_prompt("risk_manager")

    def _resolve_profile(self, db: Optional[Session]) -> Dict[str, Any]:
        """Resolve the active mode profile. Falls back to DEFAULT_PROFILE_SLUG."""
        if db is None:
            return get_profile(DEFAULT_PROFILE_SLUG) or MODE_PROFILES[DEFAULT_PROFILE_SLUG]
        try:
            return get_active_profile(db)
        except Exception as e:
            logger.warning("risk_manager_profile_lookup_failed", error=str(e))
            return get_profile(DEFAULT_PROFILE_SLUG) or MODE_PROFILES[DEFAULT_PROFILE_SLUG]

    def _build_profile_directive(self, profile: Dict[str, Any]) -> str:
        """Build the profile-aware behavioral block appended to the system prompt."""
        slug = profile.get("slug", DEFAULT_PROFILE_SLUG)
        bias = PROFILE_BIAS.get(slug, PROFILE_BIAS[DEFAULT_PROFILE_SLUG])
        params = profile.get("params", {})
        lines = [
            "",
            "=== ACTIVE TRADING PROFILE (user-selected) ===",
            f"Profile: {profile.get('name_en', slug)} ({slug}) — risk_level {profile.get('risk_level', '?')}/5",
            f"Tagline: {profile.get('tagline', '')}",
            f"Description: {profile.get('description', '')}",
            "",
            "Behavioral directive for THIS profile:",
            f"- Stance: {bias['stance']}",
            f"- Default decision: {bias['default_decision']}",
            f"- Approval bar: {bias['approve_bar']}",
            f"- Sizing bias: {bias['size_bias']}",
            f"- Leverage bias: {bias['leverage_bias']}",
            "",
            "Profile-enforced numeric limits (already applied as system settings):",
            f"- daily_loss_limit: {params.get('daily_loss_limit', '?')}%",
            f"- max_drawdown_pct: {params.get('max_drawdown_pct', '?')}%",
            f"- max_position_size: {params.get('max_position_size', '?')}%",
            f"- max_total_exposure: {params.get('max_total_exposure', '?')}%",
            f"- max_leverage: {params.get('max_leverage', '?')}x",
            f"- correlation_guard_enabled: {params.get('correlation_guard_enabled', '?')}",
            "",
            "You MUST adopt this profile's personality. Do not behave more aggressively than "
            "the profile allows, and do not behave more cautiously than it requires.",
        ]
        return "\n".join(lines)

    def evaluate_hard_rules(
        self,
        portfolio: PortfolioState,
        trade_size_usd: float,
        daily_loss_limit: float,
        max_total_exposure: float,
        max_pos_pct: float,
        max_drawdown_pct: Optional[float] = None,
    ) -> Tuple[Dict[str, Any], Optional[RiskDecision]]:
        """
        Evaluasi aturan risiko deterministik.

        Returns:
            (context, critical_override)
            - context: dict berisi status setiap rule untuk dikirim ke AI
            - critical_override: RiskDecision non-None HANYA untuk pelanggaran
              fatal (daily loss limit / max drawdown) yang tidak boleh
              di-override AI. Pelanggaran lainnya (size/exposure) hanya
              menjadi sinyal di context, AI yang memutuskan.
        """
        current_exposure = sum(p.size * p.current_price for p in portfolio.open_positions)
        new_total_exposure = current_exposure + trade_size_usd
        exposure_pct = (new_total_exposure / portfolio.total_equity) if portfolio.total_equity > 0 else 0.0
        max_size_allowed = portfolio.total_equity * (max_pos_pct / 100)
        size_pct_of_equity = (trade_size_usd / portfolio.total_equity) if portfolio.total_equity > 0 else 0.0
        effective_max_dd = max_drawdown_pct if max_drawdown_pct is not None else self.MAX_DRAWDOWN_LIMIT_PCT

        context = {
            "daily_loss_limit_pct": daily_loss_limit,
            "daily_pnl_pct": portfolio.daily_pnl_pct,
            "daily_loss_breached": portfolio.daily_pnl_pct <= -daily_loss_limit,
            "max_drawdown_limit_pct": effective_max_dd,
            "max_drawdown_pct": portfolio.max_drawdown_pct,
            "max_drawdown_breached": portfolio.max_drawdown_pct >= effective_max_dd,
            "max_position_size_pct": max_pos_pct,
            "max_position_size_usd": max_size_allowed,
            "proposed_size_pct_of_equity": size_pct_of_equity * 100,
            "size_exceeds_soft_cap": trade_size_usd > max_size_allowed,
            "size_exceeds_extreme_cap": trade_size_usd > portfolio.total_equity * 0.50,
            "max_total_exposure_pct": max_total_exposure,
            "current_exposure_pct": exposure_pct * 100,
            "exposure_would_breach": exposure_pct > (max_total_exposure / 100),
        }

        # CRITICAL safety overrides — AI cannot bypass these
        if context["daily_loss_breached"]:
            return context, RiskDecision(
                decision="REJECT",
                max_position_size_usd=0.0,
                max_leverage=1,
                reasoning=f"[CRITICAL OVERRIDE] Daily loss limit reached ({portfolio.daily_pnl_pct:.2f}%). Limit: {daily_loss_limit}%",
                risk_metrics={"daily_pnl_pct": portfolio.daily_pnl_pct, "override": "daily_loss_limit"}
            )

        if context["max_drawdown_breached"]:
            return context, RiskDecision(
                decision="REJECT",
                max_position_size_usd=0.0,
                max_leverage=1,
                reasoning=f"[CRITICAL OVERRIDE] Max drawdown reached ({portfolio.max_drawdown_pct:.2f}%). Emergency stop.",
                risk_metrics={"max_drawdown_pct": portfolio.max_drawdown_pct, "override": "max_drawdown"}
            )

        return context, None

    async def analyze(
        self,
        symbol: str,
        side: str, # "BUY" (Long) | "SELL" (Short)
        trade_size_usd: float,
        portfolio: PortfolioState,
        market_volatility: str = "normal", # low/normal/high
        db: Session = None,
        advanced: bool = False,
    ) -> RiskDecision:
        """
        Analisa risiko: AI selalu menjadi pengambil keputusan.
        Hard rules menjadi konteks; hanya pelanggaran fatal yang men-override AI.
        """
        try:
            # Step 0a: Resolve active user-selected profile (Conservative → YOLO)
            profile = self._resolve_profile(db)
            profile_params = profile.get("params", {})

            # Step 0b: Dynamic limits — pull from SystemSettings (live overrides),
            # falling back to the active profile's params so behavior matches the
            # profile even if a particular setting hasn't been persisted yet.
            def _setting(key: str, default_from_profile: str) -> str:
                if db is not None:
                    return SystemSettings.get_value(db, key, profile_params.get(key, default_from_profile))
                return profile_params.get(key, default_from_profile)

            daily_limit = float(_setting("daily_loss_limit", "12.0"))
            max_leverage = int(_setting("max_leverage", "15"))
            max_pos_pct = float(_setting("max_position_size", "20.0"))
            max_exposure = float(_setting("max_total_exposure", "80.0"))
            max_drawdown_pct = float(_setting("max_drawdown_pct", str(self.MAX_DRAWDOWN_LIMIT_PCT)))

            # Step 1: Evaluasi hard rules → dapatkan konteks + cek critical override
            hard_context, critical_override = self.evaluate_hard_rules(
                portfolio,
                trade_size_usd,
                daily_limit,
                max_exposure,
                max_pos_pct,
                max_drawdown_pct=max_drawdown_pct,
            )

            if critical_override:
                logger.info(
                    "risk_critical_override_triggered",
                    decision=critical_override.decision,
                    reason=critical_override.reasoning,
                    profile=profile.get("slug"),
                )
                return critical_override

            # Step 2: AI Reasoning — system prompt is profile-aware; user data block
            # carries the live numeric context and hard-rule findings.
            profile_directive = self._build_profile_directive(profile)
            system_prompt = f"{self.base_prompt}\n{profile_directive}"

            data_str = f"Symbol: {symbol}\nAction: {side}\nProposed Size: ${trade_size_usd}\n"
            data_str += f"\nPortfolio Status:\n{portfolio.model_dump_json(indent=2)}\n"
            data_str += f"\nMarket Volatility: {market_volatility}\n"
            data_str += f"\nRisk Limits: Daily Loss {daily_limit}%, Max Pos {max_pos_pct}%, Max Exposure {max_exposure}%, Max Leverage {max_leverage}x\n"
            data_str += f"\nActive Profile: {profile.get('slug')} (risk_level {profile.get('risk_level', '?')}/5)\n"
            data_str += f"\nHard Rule Evaluation (for your context):\n{json.dumps(hard_context, indent=2)}\n"

            instruction = (
                f"You are the FINAL decision maker, operating under the "
                f"'{profile.get('slug')}' profile. Evaluate the risk for {side} {symbol} "
                f"with size ${trade_size_usd}. Consider portfolio health, correlation across "
                f"open positions, market volatility, and the hard rule evaluation provided. "
                f"Apply the profile's behavioral directive (stance, default decision, "
                f"approval bar, sizing/leverage bias) when choosing APPROVE, REJECT, or REDUCE_SIZE."
            )

            response = await self.ai.analyze(
                system_prompt=system_prompt,
                data=data_str,
                instruction=instruction,
                json_mode=True,
                agent_name=self.AGENT_NAME,
                advanced=advanced,
            )

            # Step 3: Parse AI response
            try:
                result = json.loads(response.content)
            except json.JSONDecodeError:
                logger.error("ai_json_decode_failed", content=response.content)
                return RiskDecision(
                    decision="REJECT",
                    max_position_size_usd=0.0,
                    max_leverage=1,
                    reasoning="Gagal memproses respons AI Risk Manager.",
                )

            # Step 4: Apply safety caps — AI cannot exceed hard sizing limits
            ai_decision = result.get("decision", "REJECT")
            final_size = float(result.get("max_position_size_usd", trade_size_usd))
            hard_cap = portfolio.total_equity * (max_pos_pct / 100)

            if final_size > hard_cap:
                final_size = hard_cap
                ai_decision = "REDUCE_SIZE"
                result["reasoning"] = (
                    result.get("reasoning", "")
                    + f" (Note: Size capped at {max_pos_pct}% equity by safety layer)"
                )

            # Exposure safety cap — block any approval that would breach total exposure
            if ai_decision == "APPROVE" and hard_context["exposure_would_breach"]:
                ai_decision = "REJECT"
                result["reasoning"] = (
                    result.get("reasoning", "")
                    + f" (Note: Total exposure would exceed {max_exposure}% — blocked by safety layer)"
                )
                final_size = 0.0

            final_leverage = min(int(result.get("max_leverage", max_leverage)), max_leverage)

            return RiskDecision(
                decision=ai_decision,
                max_position_size_usd=final_size,
                max_leverage=final_leverage,
                reasoning=result.get("reasoning", "No reasoning provided."),
                risk_metrics={
                    **result.get("risk_metrics", {}),
                    "ai_driven": True,
                    "profile": profile.get("slug"),
                    "profile_risk_level": profile.get("risk_level"),
                },
            )

        except Exception as e:
            logger.error("risk_analysis_failed", error=str(e))
            return RiskDecision(
                decision="REJECT",
                max_position_size_usd=0.0,
                max_leverage=1,
                reasoning=f"Error dalam analisis risiko: {str(e)}",
            )
