"""
Technical Analyst Agent.

Menganalisa data harga menggunakan indikator teknikal dan menghasilkan
sinyal trading (BUY/SELL/HOLD) dengan confidence score.
"""

import pandas as pd
import pandas_ta as ta
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from app.core.ai_provider import AIProvider
from app.core.logging import get_logger
from app.schemas.agent_signal import AgentSignal

logger = get_logger(__name__)


class TechnicalAnalystAgent:
    """Agent yang menganalisa data harga secara teknikal."""

    AGENT_NAME = "technical_analyst"

    # System prompt yang menjelaskan siapa agent ini
    SYSTEM_PROMPT = """You are an expert Technical Analyst for cryptocurrency markets.
You analyze price data using technical indicators and produce trading signals.

Your analysis must be:
1. Data-driven — base your signal ONLY on the indicators provided.
2. Multi-timeframe — consider alignment across timeframes. 
   - A signals is much stronger if it's aligned across 15m, 1h, 4h, and 1D.
   - If timeframes conflict, prioritize the higher timeframes for trend and lower for entry.
3. Conservative — when in doubt, signal NEUTRAL.
4. Specific — state exact indicator values that support your conclusion.

Output MUST be valid JSON with this structure:
{
    "signal": "STRONG_BUY" | "BUY" | "NEUTRAL" | "SELL" | "STRONG_SELL",
    "confidence": 0.0 to 1.0,
    "reasoning": "explanation in 2-3 sentences",
    "key_levels": {
        "support": [price1, price2],
        "resistance": [price1, price2]
    },
    "indicators_summary": {
        "trend": "bullish" | "bearish" | "neutral",
        "momentum": "bullish" | "bearish" | "neutral",
        "volatility": "high" | "normal" | "low"
    },
    "alignment": {
        "is_aligned": true/false,
        "details": "e.g. 4H and 1D are bullish, 15m is neutral"
    }
}"""

    def __init__(self, ai_provider: AIProvider):
        self.ai = ai_provider

    def calculate_indicators(self, df: pd.DataFrame) -> dict:
        """
        Hitung semua indikator teknikal dari data candlestick.
        """
        if df.empty or len(df) < 50: # Perlu minimal data untuk EMA200 dll
            return {}

        indicators = {}

        # RSI (Relative Strength Index)
        rsi = ta.rsi(df["close"], length=14)
        indicators["rsi"] = round(rsi.iloc[-1], 2) if not pd.isna(rsi.iloc[-1]) else 50.0

        # MACD
        macd = ta.macd(df["close"])
        if macd is not None and not macd.empty:
            indicators["macd"] = {
                "macd_line": round(macd.iloc[-1, 0], 4),
                "signal_line": round(macd.iloc[-1, 1], 4),
                "histogram": round(macd.iloc[-1, 2], 4),
            }

        # Bollinger Bands
        bbands = ta.bbands(df["close"], length=20, std=2)
        if bbands is not None and not bbands.empty:
            indicators["bollinger"] = {
                "upper": round(bbands.iloc[-1, 0], 2),
                "middle": round(bbands.iloc[-1, 1], 2),
                "lower": round(bbands.iloc[-1, 2], 2),
                "current_price": round(df["close"].iloc[-1], 2),
            }

        # EMA (Exponential Moving Averages)
        for period in [9, 21, 50, 200]:
            ema = ta.ema(df["close"], length=period)
            if ema is not None and not ema.empty:
                indicators[f"ema_{period}"] = round(ema.iloc[-1], 2) if not pd.isna(ema.iloc[-1]) else None

        # ATR (Average True Range)
        atr = ta.atr(df["high"], df["low"], df["close"], length=14)
        if atr is not None and not atr.empty:
            indicators["atr"] = round(atr.iloc[-1], 2)

        # Volume analysis
        avg_vol = df["volume"].tail(20).mean()
        indicators["volume"] = {
            "current": float(df["volume"].iloc[-1]),
            "avg_20": round(float(avg_vol), 2),
            "above_average": bool(df["volume"].iloc[-1] > avg_vol),
        }

        # Ichimoku Cloud (Basic)
        ichimoku, span = ta.ichimoku(df["high"], df["low"], df["close"])
        if ichimoku is not None and not ichimoku.empty:
            indicators["ichimoku"] = {
                "tenkan": round(ichimoku.iloc[-1, 0], 2),
                "kijun": round(ichimoku.iloc[-1, 1], 2),
                "senkou_a": round(span.iloc[-1, 0], 2),
                "senkou_b": round(span.iloc[-1, 1], 2),
            }

        # Current price
        indicators["current_price"] = round(float(df["close"].iloc[-1]), 2)

        return indicators

    def _detect_tf_alignment(self, all_indicators: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deteksi keselarasan sinyal di berbagai timeframe.
        """
        alignment = {"is_aligned": False, "details": ""}
        trends = {}

        for tf, ind in all_indicators.items():
            if not ind: continue
            
            # Simple trend detection per TF: Close > EMA50?
            ema50 = ind.get("ema_50")
            price = ind.get("current_price")
            if ema50 and price:
                trends[tf] = "bullish" if price > ema50 else "bearish"
            else:
                trends[tf] = "neutral"

        # Check if all available TFs are same
        if trends:
            unique_trends = set(trends.values())
            if len(unique_trends) == 1 and "neutral" not in unique_trends:
                alignment["is_aligned"] = True
                alignment["details"] = f"All timeframes ({', '.join(trends.keys())}) are {list(unique_trends)[0]}"
            else:
                alignment["details"] = ", ".join([f"{tf}: {t}" for tf, t in trends.items()])

        return alignment

    async def analyze(
        self,
        symbol: str,
        candles_by_timeframe: Dict[str, List[Dict]],
    ) -> AgentSignal:
        """
        Analisa teknikal lengkap pada satu trading pair.
        """
        try:
            # Step 1: Hitung indikator untuk setiap timeframe
            all_indicators = {}
            for tf, candles in candles_by_timeframe.items():
                df = pd.DataFrame(candles)
                all_indicators[tf] = self.calculate_indicators(df)

            # Step 2: Deteksi alignment (T-4.2)
            alignment = self._detect_tf_alignment(all_indicators)

            # Step 3: Kirim ke AI untuk interpretasi
            data_str = f"Symbol: {symbol}\n\nIndicators by Timeframe:\n"
            for tf, indicators in all_indicators.items():
                data_str += f"\n=== {tf.upper()} ===\n{indicators}\n"
            
            data_str += f"\n=== Alignment Detection ===\n{alignment}\n"

            instruction = (
                f"Analyze the technical indicators for {symbol} across all timeframes. "
                f"Prioritize higher timeframes for trend and lower for entry timing. "
                f"Produce a JSON trading signal. If alignment is true, boost confidence."
            )

            response = await self.ai.analyze(
                system_prompt=self.SYSTEM_PROMPT,
                data=data_str,
                instruction=instruction,
                json_mode=True,
            )

            # Step 4: Parse response AI
            try:
                result = json.loads(response.content)
            except json.JSONDecodeError:
                # Handle non-JSON output fallback
                logger.error("ai_json_decode_failed", content=response.content)
                return AgentSignal(
                    agent_name=self.AGENT_NAME,
                    symbol=symbol,
                    signal="NEUTRAL",
                    confidence=0.0,
                    reasoning="Gagal memproses respons AI.",
                )

            # Create AgentSignal
            return AgentSignal(
                agent_name=self.AGENT_NAME,
                symbol=symbol,
                signal=result.get("signal", "NEUTRAL"),
                confidence=result.get("confidence", 0.0),
                reasoning=result.get("reasoning", "No reasoning provided."),
                metadata={
                    "indicators": all_indicators,
                    "key_levels": result.get("key_levels", {}),
                    "indicators_summary": result.get("indicators_summary", {}),
                    "alignment": result.get("alignment", alignment),
                },
            )

        except Exception as e:
            logger.error("technical_analysis_failed", error=str(e))
            return AgentSignal(
                agent_name=self.AGENT_NAME,
                symbol=symbol,
                signal="NEUTRAL",
                confidence=0.0,
                reasoning=f"Error dalam analisis teknikal: {str(e)}",
            )
