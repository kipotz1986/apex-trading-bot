"""
Regime-Based Behavior Switching.

Mengatur parameter trading (threshold, position sizing, stop loss)
berdasarkan regime pasar yang terdeteksi.
"""

from typing import Dict, Any

class RegimeStrategy:
    """Service untuk menentukan strategi berdasarkan regime."""

    # Config per regime
    # [min_confidence, max_size_multiplier, risk_multiplier]
    # Very Aggressive: low confidence floors, full size in trends, high leverage caps
    CONFIGS = {
        "trending_up": {
            "min_confidence": 0.30,
            "max_size_mult": 1.0,
            "risk_mult": 1.2,
            "leverage_cap": 15
        },
        "trending_down": {
            "min_confidence": 0.30,
            "max_size_mult": 1.0,
            "risk_mult": 1.2,
            "leverage_cap": 15
        },
        "sideways": {
            "min_confidence": 0.35,
            "max_size_mult": 1.0,
            "risk_mult": 1.0,
            "leverage_cap": 10
        },
        "high_volatility": {
            "min_confidence": 0.40,
            "max_size_mult": 0.8,
            "risk_mult": 0.9,
            "leverage_cap": 8
        },
        "unknown": {
            "min_confidence": 0.35,
            "max_size_mult": 0.8,
            "risk_mult": 0.9,
            "leverage_cap": 8
        }
    }

    def get_params(self, regime: str) -> Dict[str, Any]:
        """Ambil parameter strategi untuk regime tertentu."""
        return self.CONFIGS.get(regime, self.CONFIGS["unknown"])

    def adjust_decision(
        self,
        decision: Dict[str, Any],
        regime_data: Dict[str, Any],
        user_threshold: float = None,
    ) -> Dict[str, Any]:
        """
        Sesuaikan TradeDecision berdasarkan regime pasar.

        user_threshold: when provided, overrides the hardcoded min_confidence so
        that the user's consensus sensitivity settings are actually respected.
        """
        regime = regime_data.get("regime", "unknown")
        params = self.get_params(regime)

        # Effective confidence floor: honour the user's explicit setting when it
        # is lower than the regime default (i.e. user chose to be aggressive).
        min_conf = params["min_confidence"]
        if user_threshold is not None:
            min_conf = min(min_conf, user_threshold)

        # 1. Check confidence threshold
        decision["confidence"] = min(float(decision.get("confidence", 0.0)), 1.0)
        if decision["confidence"] < min_conf:
            decision["action"] = "HOLD"
            decision["reasoning"] += f" (Regime {regime} requires confidence > {min_conf:.2f})"

        # 2. Adjust size
        decision["proposed_size"] *= params["max_size_mult"]

        # 3. Adjust leverage
        if decision.get("leverage", 1) > params["leverage_cap"]:
            decision["leverage"] = params["leverage_cap"]

        return decision
