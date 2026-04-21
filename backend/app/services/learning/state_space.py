"""
State Space Service.

Membangun vektor numerik dari kondisi pasar dan portfolio 
untuk dikonsumsi oleh model Reinforcement Learning.
"""

import numpy as np
from typing import Dict, Any, List
from app.schemas.portfolio import PortfolioState

class StateSpace:
    """Service untuk membangun state vector RL."""

    def __init__(self, feature_dim: int = 25):
        self.feature_dim = feature_dim

    def build_vector(
        self, 
        market_data: Dict[str, Any], 
        portfolio: PortfolioState,
        agent_signals: Dict[str, Any]
    ) -> np.ndarray:
        """
        Input: Market data, portfolio state, dan sinyal analis.
        Output: Numpy array (1, feature_dim) ter-normalisasi.
        """
        features = []
        
        # 1. Market Indicators (Normalized)
        candles = market_data.get("candles", [])
        if candles:
            # Simplest version: last 5 close price changes
            closes = [c["close"] for c in candles[-6:]]
            if len(closes) >= 2:
                pct_changes = [(closes[i] - closes[i-1])/closes[i-1] for i in range(1, len(closes))]
                # Pad if data missing
                while len(pct_changes) < 5: pct_changes.append(0.0)
                features.extend(pct_changes[:5])
            else:
                features.extend([0.0] * 5)
        else:
            features.extend([0.0] * 5)
            
        # 2. Sentiment Indicators
        features.append(market_data.get("fear_greed_index", 50) / 100.0)
        
        # 3. Portfolio State
        features.append(portfolio.total_equity / (portfolio.total_balance + 1e-6)) # Equity ratio
        features.append(portfolio.available_margin / (portfolio.total_balance + 1e-6)) # Margin ratio
        features.append(portfolio.daily_pnl_pct / 5.0) # Normalized to [-1, 1] range (max 5% daily loss)
        
        # 4. Agent Signals (Normalized to -1, 0, 1)
        # BUY = 1, SELL = -1, NEUTRAL = 0
        agent_map = {"BUY": 1.0, "STRONG_BUY": 1.0, "SELL": -1.0, "STRONG_SELL": -1.0, "NEUTRAL": 0.0}
        
        agents = ["technical", "fundamental", "sentiment", "copy_trader"]
        for a in agents:
            sig_obj = agent_signals.get(a)
            sig_val = sig_obj.signal if hasattr(sig_obj, "signal") else str(sig_obj)
            features.append(agent_map.get(sig_val, 0.0))
            features.append(sig_obj.confidence if hasattr(sig_obj, "confidence") else 0.0)

        # 5. Volatility (ATR-like)
        if candles and "high" in candles[-1] and "low" in candles[-1]:
            last_vol = (candles[-1]["high"] - candles[-1]["low"]) / candles[-1]["close"]
            features.append(min(last_vol * 10, 1.0)) # Scaled
        else:
            features.append(0.0)

        # Fill remaining with padding to reach feature_dim
        while len(features) < self.feature_dim:
            features.append(0.0)
            
        return np.array(features[:self.feature_dim], dtype=np.float32)
