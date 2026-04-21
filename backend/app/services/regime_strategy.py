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
    CONFIGS = {
        "trending_up": {
            "min_confidence": 0.60,
            "max_size_mult": 1.0,
            "risk_mult": 1.0,
            "leverage_cap": 5
        },
        "trending_down": {
            "min_confidence": 0.60,
            "max_size_mult": 1.0,
            "risk_mult": 1.0,
            "leverage_cap": 5
        },
        "sideways": {
            "min_confidence": 0.80,
            "max_size_mult": 0.5,
            "risk_mult": 0.7,
            "leverage_cap": 2
        },
        "high_volatility": {
            "min_confidence": 0.90,
            "max_size_mult": 0.25,
            "risk_mult": 0.5,
            "leverage_cap": 1
        },
        "unknown": {
            "min_confidence": 0.85,
            "max_size_mult": 0.3,
            "risk_mult": 0.5,
            "leverage_cap": 1
        }
    }

    def get_params(self, regime: str) -> Dict[str, Any]:
        """Ambil parameter strategi untuk regime tertentu."""
        return self.CONFIGS.get(regime, self.CONFIGS["unknown"])

    def adjust_decision(self, decision: Dict[str, Any], regime_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sesuaikan TradeDecision berdasarkan regime pasar.
        """
        regime = regime_data.get("regime", "unknown")
        params = self.get_params(regime)
        
        # 1. Check confidence threshold
        if decision["confidence"] < params["min_confidence"]:
            decision["action"] = "HOLD"
            decision["reasoning"] += f" (Regime {regime} requires confidence > {params['min_confidence']})"
            
        # 2. Adjust size
        decision["proposed_size"] *= params["max_size_mult"]
        
        # 3. Adjust leverage
        if decision.get("leverage", 1) > params["leverage_cap"]:
            decision["leverage"] = params["leverage_cap"]
            
        return decision
