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

    def __init__(self, initial_weights: Dict[str, float] = None):
        """
        Args:
            initial_weights: Bobot default untuk setiap agent.
                             Total harus 1.0.
        """
        self.agent_weights = initial_weights or {
            "technical": 0.30,
            "fundamental": 0.25,
            "sentiment": 0.20,
            "copy_trader": 0.25
        }

    def calculate(self, signals: Dict[str, AgentSignal]) -> Dict[str, Any]:
        """
        Hitung skor konsensus terbobot.
        
        Formula: Σ (signal_value * confidence * agent_weight)
        """
        total_score = 0.0
        used_weights = 0.0
        applied_signals = {}
        
        has_strong_buy = False
        has_strong_sell = False

        for agent_name, signal_obj in signals.items():
            if not signal_obj:
                continue
                
            label = signal_obj.signal.upper()
            numeric_val = self.SIGNAL_WEIGHTS.get(label, 0.0)
            
            # Detect sharp conflicts
            if label == "STRONG_BUY": has_strong_buy = True
            if label == "STRONG_SELL": has_strong_sell = True
            
            # Get agent weight
            weight = self.agent_weights.get(agent_name, 0.0)
            
            # Weighted contribution
            contribution = numeric_val * signal_obj.confidence * weight
            total_score += contribution
            used_weights += weight
            
            applied_signals[agent_name] = {
                "label": label,
                "confidence": signal_obj.confidence,
                "weight": weight,
                "contribution": round(contribution, 4)
            }

        # Normalize score jika ada agent yang absen (opsional, tapi di sini kita pakai absolute logic)
        # Threshold Logic:
        # Score > 0.7 -> STRONG EXECUTE (BUY)
        # Score > 0.4 -> EXECUTE (BUY)
        # Score < -0.7 -> STRONG EXECUTE (SELL)
        # Score < -0.4 -> EXECUTE (SELL)
        # Else -> HOLD
        
        abs_score = abs(total_score)
        action = "HOLD"
        confidence = abs_score # Initial confidence is the score itself
        
        if total_score >= 0.7:
            action = "EXECUTE_LONG"
        elif total_score >= 0.4:
            action = "EXECUTE_LONG" # Or "WAIT_RETRACEMENT"
        elif total_score <= -0.7:
            action = "EXECUTE_SHORT"
        elif total_score <= -0.4:
            action = "EXECUTE_SHORT"

        # Conflict Detection
        has_conflict = has_strong_buy and has_strong_sell
        
        result = {
            "score": round(total_score, 4),
            "action": action,
            "confidence": round(abs_score, 2),
            "has_conflict": has_conflict,
            "proposed_size": 100.0, # Default size, will be refined by Risk Manager
            "reasoning": self._generate_reasoning(action, total_score, has_conflict),
            "breakdown": applied_signals
        }
        
        logger.info("consensus_calculated", score=result["score"], action=action, conflict=has_conflict)
        return result

    def _generate_reasoning(self, action: str, score: float, conflict: bool) -> str:
        """Helper untuk generate reasoning teks awal."""
        if conflict:
            return "Terjadi konflik tajam antara sinyal STRONG_BUY dan STRONG_SELL. Menunggu keputusan Judge."
        
        if action == "HOLD":
            return f"Konsensus lemah (Score: {score:.2f}). Tidak cukup keyakinan untuk membuka posisi."
        
        dir_str = "Bullish" if score > 0 else "Bearish"
        strength = "Kuat" if abs(score) > 0.7 else "Moderat"
        return f"Konsensus {strength} {dir_str} terdeteksi (Score: {score:.2f})."
