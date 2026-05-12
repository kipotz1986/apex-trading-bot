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

    # Coin → one-hot index. Adding new coins appends; existing indices stay stable.
    COIN_INDEX: Dict[str, int] = {"BTC": 0, "ETH": 1, "SOL": 2}
    # Total: 25 base features + len(COIN_INDEX) one-hot symbol features
    BASE_DIM = 25

    def __init__(self, feature_dim: int = None):
        # Auto-size: 25 base + 3 coin slots = 28. Allow override for legacy models.
        self.feature_dim = feature_dim or (self.BASE_DIM + len(self.COIN_INDEX))

    def build_vector(
        self,
        market_data: Dict[str, Any],
        portfolio: PortfolioState,
        agent_signals: Dict[str, Any],
        symbol: str = None,
    ) -> np.ndarray:
        """
        Input: Market data, portfolio state, dan sinyal analis.
        Output: Numpy array (1, feature_dim) ter-normalisasi.
        """
        features = []
        
        # 1. Market Indicators (Normalized)
        candles_dict = market_data.get("candles", {})
        # Use 1h for state vector, or fallback to any available timeframe
        candles = candles_dict.get("1h") or (next(iter(candles_dict.values()), []) if candles_dict else [])
        
        if candles:
            # Simplest version: last 5 close price changes
            # Handle both objects and dicts for backward compatibility
            get_close = lambda c: c.close if hasattr(c, 'close') else c.get('close', 0)
            closes = [get_close(c) for c in candles[-6:]]
            if len(closes) >= 2:
                pct_changes = [(closes[i] - closes[i-1])/closes[i-1] if closes[i-1] != 0 else 0.0 for i in range(1, len(closes))]
                # Pad if data missing
                while len(pct_changes) < 5: pct_changes.append(0.0)
                features.extend(pct_changes[:5])
            else:
                features.extend([0.0] * 5)
        else:
            features.extend([0.0] * 5)
            
        # 2. Sentiment Indicators
        composite = market_data.get("composite_sentiment")
        fng_value = (composite.score + 100) / 200.0 if composite else 0.5  # Normalize -100..100 ke 0..1
        features.append(fng_value)        
        # 3. Portfolio State
        features.append(portfolio.total_equity / (portfolio.total_balance + 1e-6)) # Equity ratio
        features.append(portfolio.available_margin / (portfolio.total_balance + 1e-6)) # Margin ratio
        features.append(portfolio.daily_pnl_pct / 5.0) # Normalized to [-1, 1] range (max 5% daily loss)
        
        # 4. Agent Signals (Normalized to -1, 0, 1)
        # BUY = 1, SELL = -1, NEUTRAL = 0
        agent_map = {"BUY": 1.0, "STRONG_BUY": 1.0, "SELL": -1.0, "STRONG_SELL": -1.0, "NEUTRAL": 0.0}
        
        agents = ["technical", "fundamental", "sentiment"]
        for a in agents:
            sig_obj = agent_signals.get(a)
            sig_val = sig_obj.signal if hasattr(sig_obj, "signal") else str(sig_obj)
            features.append(agent_map.get(sig_val, 0.0))
            features.append(sig_obj.confidence if hasattr(sig_obj, "confidence") else 0.0)

        # 5. Volatility (ATR-like)
        if candles:
            last = candles[-1]
            get_val = lambda obj, key: getattr(obj, key) if hasattr(obj, key) else obj.get(key, 0)
            h, l, c = get_val(last, 'high'), get_val(last, 'low'), get_val(last, 'close')
            last_vol = (h - l) / c if c != 0 else 0
            features.append(min(last_vol * 10, 1.0)) # Scaled
        else:
            features.append(0.0)

        # 6. Exchange Sentiment (Funding Rate & Open Interest)
        exch_sent = market_data.get("exchange_sentiment", {})
        features.append(max(min(float(exch_sent.get("funding_rate", 0.0)) * 1000, 1.0), -1.0)) # Scaled funding rate
        features.append(min(float(exch_sent.get("open_interest", 0.0)) / 1e9, 1.0)) # Scaled OI in billions
        
        # 7. Onchain Stats
        onchain = market_data.get("onchain_stats", {})
        features.append(min(float(onchain.get("hash_rate", 0.0) or 0.0) / 1e12, 1.0))
        features.append(min(float(onchain.get("unconfirmed_txs", 0.0) or 0.0) / 100000.0, 1.0))
        features.append(min(float(onchain.get("mempool_size", 0.0) or 0.0) / 1e9, 1.0))
        
        # 8. Extra candle metrics
        if candles:
            last = candles[-1]
            get_val = lambda obj, key: getattr(obj, key) if hasattr(obj, key) else obj.get(key, 0)
            features.append(min(float(get_val(last, 'volume')) / 10000.0, 1.0))
            features.append(min(float(get_val(last, 'close')) / 100000.0, 1.0)) # scaled price
            
            # Relation (last vs 5 ago)
            if len(candles) >= 6:
                c5 = float(get_close(candles[-6]))
                c1 = float(get_close(candles[-1]))
                features.append(min(max((c1 - c5) / c5 if c5 > 0 else 0.0, -1.0), 1.0))
            else:
                features.append(0.0)
        else:
            features.extend([0.0] * 3)

        # 9. Time of day (normalized 0-1)
        from datetime import datetime
        features.append(datetime.utcnow().hour / 24.0)

        # 10. Symbol one-hot encoding — lets RL learn distinct policies per coin
        coin = (symbol or "").split('/')[0].upper() if symbol else ""
        coin_one_hot = [0.0] * len(self.COIN_INDEX)
        if coin in self.COIN_INDEX:
            coin_one_hot[self.COIN_INDEX[coin]] = 1.0
        features.extend(coin_one_hot)

        # Fill remaining with padding to reach feature_dim (just in case)
        while len(features) < self.feature_dim:
            features.append(0.0)

        return np.array(features[:self.feature_dim], dtype=np.float32)
