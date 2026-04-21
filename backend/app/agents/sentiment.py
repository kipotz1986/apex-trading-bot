"""
Sentiment Analyst Agent.

Menganalisa psikologi pasar berdasarkan Fear & Greed Index,
Funding Rates, dan Open Interest.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from app.core.ai_provider import AIProvider
from app.core.logging import get_logger
from app.schemas.agent_signal import AgentSignal
from app.schemas.market_data import NormalizedSentiment
from app.utils.prompts import get_prompt

logger = get_logger(__name__)


class SentimentAnalystAgent:
    """Agent yang menganalisa mood dan sentimen pasar."""

    AGENT_NAME = "sentiment_analyst"

    def __init__(self, ai_provider: AIProvider):
        self.ai = ai_provider
        self.system_prompt = get_prompt("sentiment_analyst")

    async def analyze(
        self,
        symbol: str,
        composite_sentiment: NormalizedSentiment,
        exchange_sentiment: Dict[str, Any],
    ) -> AgentSignal:
        """
        Analisa sentimen lengkap berdasarkan data agregat dan exchange.
        """
        try:
            # Step 1: Format data untuk AI
            data_str = f"Symbol: {symbol}\n\nComposite Sentiment Data:\n{composite_sentiment.model_dump()}\n"
            data_str += f"\nExchange Sentiment (Funding & OI):\n{json.dumps(exchange_sentiment, indent=2)}\n"

            instruction = (
                f"Analyze the market sentiment for {symbol}. "
                f"Look for extreme fear/greed levels and overleverage in funding rates. "
                f"Produce a JSON trading signal with confidence score."
            )

            # Step 2: Kirim ke AI untuk interpretasi
            response = await self.ai.analyze(
                system_prompt=self.system_prompt,
                data=data_str,
                instruction=instruction,
                json_mode=True,
            )

            # Step 3: Parse response AI
            try:
                result = json.loads(response.content)
            except json.JSONDecodeError:
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
                    "sentiment_classification": result.get("sentiment_classification", composite_sentiment.classification),
                    "risk_level": result.get("risk_level", "normal"),
                    "composite_score": composite_sentiment.score,
                    "funding_rate": exchange_sentiment.get("funding_rate", 0.0),
                    "open_interest": exchange_sentiment.get("open_interest", 0.0)
                },
            )

        except Exception as e:
            logger.error("sentiment_analysis_failed", error=str(e))
            return AgentSignal(
                agent_name=self.AGENT_NAME,
                symbol=symbol,
                signal="NEUTRAL",
                confidence=0.0,
                reasoning=f"Error dalam analisis sentimen: {str(e)}",
            )
