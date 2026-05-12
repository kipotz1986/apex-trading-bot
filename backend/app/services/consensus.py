"""
Consensus Engine.

Mesin voting terbobot (Weighted Voting) untuk merangkum sinyal
dari berbagai agent analis menjadi satu skor konsensus.
"""

from typing import Dict, Any, List
from app.schemas.agent_signal import AgentSignal
from app.core.logging import get_logger

logger = get_logger(__name__)


class ConsensusEngine:
    """Engine untuk kalkulasi konsensus multi-agent."""

    # Nilai numerik untuk setiap label sinyal
    SIGNAL_WEIGHTS = {
        "STRONG_BUY": 1.0,
        "BUY": 0.5,
        "NEUTRAL": 0.0,
        "SELL": -0.5,
        "STRONG_SELL": -1.0
    }

    def __init__(self, initial_weights: Dict[str, float] = None, thresholds: Dict[str, float] = None):
        """
        Args:
            initial_weights: Bobot default untuk setiap agent.
            thresholds: Threshold untuk aksi (strong, moderate).
        """
        self.agent_weights = initial_weights or {
            "technical": 0.40,
            "fundamental": 0.30,
            "sentiment": 0.30
        }
        # Very Aggressive: low bar for execution — fires on weak signals
        self.thresholds = thresholds or {
            "strong": 0.4,
            "moderate": 0.15
        }

    def calculate(self, signals: Dict[str, AgentSignal], custom_thresholds: Dict[str, float] = None) -> Dict[str, Any]:
        """
        Hitung skor konsensus terbobot.
        
        Formula: Σ (signal_value * confidence * agent_weight)
        """
        thresholds = custom_thresholds or self.thresholds
        total_score = 0.0
        active_weight_sum = 0.0   # sum of weights for agents that actually contributed
        weighted_confidence_sum = 0.0
        applied_signals = {}

        has_strong_buy = False
        has_strong_sell = False

        for agent_name, signal_obj in signals.items():
            if not signal_obj:
                continue

            label = signal_obj.signal.upper()
            numeric_val = self.SIGNAL_WEIGHTS.get(label, 0.0)

            if label == "STRONG_BUY": has_strong_buy = True
            if label == "STRONG_SELL": has_strong_sell = True

            weight = self.agent_weights.get(agent_name, 0.0)
            contribution = numeric_val * signal_obj.confidence * weight
            total_score += contribution

            if signal_obj.confidence > 0:
                active_weight_sum += weight
                weighted_confidence_sum += signal_obj.confidence * weight

            applied_signals[agent_name] = {
                "label": label,
                "confidence": signal_obj.confidence,
                "weight": weight,
                "contribution": round(contribution, 4)
            }

        # Normalize score by active weights so thresholds remain stable when agents fail
        if active_weight_sum > 0:
            normalized_score = total_score / active_weight_sum
            confidence = weighted_confidence_sum / active_weight_sum
        else:
            normalized_score = 0.0
            confidence = 0.0

        action = "HOLD"
        logger.info("consensus_debug", raw_score=total_score, normalized=normalized_score,
                    active_weights=active_weight_sum, mod=thresholds["moderate"], strong=thresholds["strong"])

        if normalized_score >= thresholds["strong"]:
            action = "EXECUTE_LONG"
        elif normalized_score >= thresholds["moderate"]:
            action = "EXECUTE_LONG"
        elif normalized_score <= -thresholds["strong"]:
            action = "EXECUTE_SHORT"
        elif normalized_score <= -thresholds["moderate"]:
            action = "EXECUTE_SHORT"

        has_conflict = has_strong_buy and has_strong_sell

        result = {
            "score": round(normalized_score, 4),
            "action": action,
            "confidence": round(min(max(confidence, 0.0), 1.0), 4),
            "has_conflict": has_conflict,
            "reasoning": self._generate_reasoning(action, normalized_score, has_conflict),
            "breakdown": applied_signals
        }
        
        logger.info("consensus_calculated", score=result["score"], action=action, conflict=has_conflict)
        return result

    def _generate_reasoning(self, action: str, score: float, conflict: bool) -> str:
        """Helper untuk generate reasoning teks awal."""
        if conflict:
            return "Terjadi konflik tajam antara sinyal STRONG_BUY dan STRONG_SELL. Menunggu keputusan Judge."

        if action == "HOLD":
            return f"Sinyal terlalu lemah untuk eksekusi (Score: {score:.2f}). Pasar belum memberikan arah yang jelas."

        dir_str = "Bullish" if score > 0 else "Bearish"
        strength = "Kuat" if abs(score) > 0.4 else "Moderat"  # threshold aligned with aggressive consensus
        return f"Konsensus {strength} {dir_str} terdeteksi (Score: {score:.2f})."
