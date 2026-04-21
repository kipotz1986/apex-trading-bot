"""
Fundamental Analyst Agent.

Menganalisa berita, data on-chain, dan event makroekonomi
untuk memberikan perspektif fundamental terhadap pasar.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from app.core.ai_provider import AIProvider
from app.core.logging import get_logger
from app.schemas.agent_signal import AgentSignal
from app.schemas.market_data import NormalizedNews, NormalizedSentiment

logger = get_logger(__name__)


class FundamentalAnalystAgent:
    """Agent yang menganalisa fundamental pasar kripto."""

    AGENT_NAME = "fundamental_analyst"

    # System prompt
    SYSTEM_PROMPT = """You are an expert Fundamental Analyst for cryptocurrency markets.
You analyze news feeds, on-chain metrics, and macro events to produce trading signals.

Your analysis must be:
1. Context-aware — evaluate news impact based on source and importance.
2. Fact-driven — on-chain data (wholesale moves, network stats) reveals real market behavior.
3. Logical — explain how specific news or on-chain metrics lead to your conclusion.
4. Objective — differentiate between noise and significant market-moving events.

Output MUST be valid JSON with this structure:
{
    "signal": "STRONG_BUY" | "BUY" | "NEUTRAL" | "SELL" | "STRONG_SELL",
    "confidence": 0.0 to 1.0,
    "reasoning": "explanation in 2-3 sentences based on news and on-chain data",
    "key_factors": [
        "factor 1 (e.g. BTC ETF inflow)",
        "factor 2 (e.g. Regulatory news)"
    ],
    "onchain_impact": "bullish" | "bearish" | "neutral",
    "news_impact": "bullish" | "bearish" | "neutral"
}"""

    def __init__(self, ai_provider: AIProvider):
        self.ai = ai_provider

    async def analyze(
        self,
        symbol: str,
        news: List[NormalizedNews],
        onchain_summary: NormalizedSentiment,
        onchain_stats: Dict[str, Any] = None,
    ) -> AgentSignal:
        """
        Analisa fundamental lengkap berdasarkan berita dan data on-chain.
        """
        try:
            # Step 1: Format data untuk AI
            news_data = []
            for item in news[:10]: # Batasi 10 berita terbaru
                 news_data.append({
                     "title": item.title,
                     "importance": item.importance,
                     "source": item.source,
                     "sentiment": item.sentiment_score
                 })

            data_str = f"Symbol: {symbol}\n\nLatest News:\n{json.dumps(news_data, indent=2)}\n"
            data_str += f"\nOn-Chain Summary:\n{onchain_summary.model_dump()}\n"
            if onchain_stats:
                data_str += f"\nOn-Chain Metrics:\n{json.dumps(onchain_stats, indent=2)}\n"

            instruction = (
                f"Analyze the provided fundamental data for {symbol}. "
                f"Identify major market drivers from news and on-chain trends. "
                f"Produce a JSON trading signal with confidence score."
            )

            # Step 2: Kirim ke AI untuk interpretasi
            response = await self.ai.analyze(
                system_prompt=self.SYSTEM_PROMPT,
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
                    "key_factors": result.get("key_factors", []),
                    "onchain_impact": result.get("onchain_impact", "neutral"),
                    "news_impact": result.get("news_impact", "neutral"),
                    "news_count": len(news),
                    "onchain_score": onchain_summary.score
                },
            )

        except Exception as e:
            logger.error("fundamental_analysis_failed", error=str(e))
            return AgentSignal(
                agent_name=self.AGENT_NAME,
                symbol=symbol,
                signal="NEUTRAL",
                confidence=0.0,
                reasoning=f"Error dalam analisis fundamental: {str(e)}",
            )
