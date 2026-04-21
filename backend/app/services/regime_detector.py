"""
Market Regime Detector.

Mendeteksi kondisi pasar saat ini (Regime) berdasarkan indikator teknikal:
1. Trending Up
2. Trending Down
3. Sideways (Range)
4. High Volatility (Crash/Pump risk)
"""

import pandas as pd
import numpy as np
try:
    import pandas_ta as ta
    HAS_PANDAS_TA = True
except ImportError:
    ta = None
    HAS_PANDAS_TA = False

from typing import Dict, Any, List
from app.core.logging import get_logger

logger = get_logger(__name__)

class RegimeDetector:
    """Service untuk mendeteksi regime pasar."""

    def detect(self, candles: List[Dict]) -> Dict[str, Any]:
        """
        Input: List of candles
        Output: { "regime": "trending_up", "confidence": 0.8, "metrics": {...} }
        """
        if not candles or len(candles) < 50:
            return {"regime": "unknown", "confidence": 0.0, "metrics": {}}

        df = pd.DataFrame(candles)
        
        if not HAS_PANDAS_TA:
            # Fallback sangat sederhana jika pandas-ta tidak ada
            return self._fallback_detection(df)

        metrics = {}
        
        # 1. Trend Strength (ADX)
        # ADX > 25 = Trending, ADX < 20 = Sideways
        adx_df = ta.adx(df["high"], df["low"], df["close"], length=14)
        if adx_df is not None:
            metrics["adx"] = float(adx_df.iloc[-1, 0])
            metrics["dmp"] = float(adx_df.iloc[-1, 1])
            metrics["dmn"] = float(adx_df.iloc[-1, 2])

        # 2. Volatility (ATR Ratio)
        atr = ta.atr(df["high"], df["low"], df["close"], length=14)
        if atr is not None:
            current_atr = float(atr.iloc[-1])
            avg_atr = float(atr.tail(50).mean())
            metrics["atr_ratio"] = current_atr / avg_atr if avg_atr > 0 else 1.0

        # 3. EMA Crossover (Trend Direction)
        ema50 = ta.ema(df["close"], length=50)
        ema200 = ta.ema(df["close"], length=200)
        if ema50 is not None and ema200 is not None:
            metrics["ema_cross"] = float(ema50.iloc[-1] - ema200.iloc[-1])
            metrics["price_vs_ema50"] = float(df["close"].iloc[-1] - ema50.iloc[-1])

        # Classification Logic
        regime = "sideways"
        confidence = 0.5
        
        adx = metrics.get("adx", 0)
        atr_ratio = metrics.get("atr_ratio", 1.0)
        ema_diff = metrics.get("ema_cross", 0)
        
        # Volatility check first (Highest priority)
        if atr_ratio > 2.0:
            regime = "high_volatility"
            confidence = min(0.9, (atr_ratio - 1.0) / 2.0)
        # Trending Check
        elif adx > 25:
            if ema_diff > 0:
                regime = "trending_up"
            else:
                regime = "trending_down"
            confidence = min(0.9, adx / 50.0)
        # Sideways Check
        elif adx < 20:
            regime = "sideways"
            confidence = (25 - adx) / 10.0
            
        logger.info("regime_detected", regime=regime, confidence=confidence)
        return {
            "regime": regime,
            "confidence": round(confidence, 2),
            "metrics": metrics
        }

    def _fallback_detection(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Simple fallback detection without pandas-ta."""
        # Just use simple price momentum
        returns = df["close"].pct_change().tail(20)
        vol = returns.std()
        avg_vol = df["close"].pct_change().std()
        
        regime = "sideways"
        if vol > avg_vol * 1.5:
            regime = "high_volatility"
        elif returns.mean() > 0.001:
            regime = "trending_up"
        elif returns.mean() < -0.001:
            regime = "trending_down"
            
        return {"regime": regime, "confidence": 0.4, "metrics": {"is_fallback": True}}
