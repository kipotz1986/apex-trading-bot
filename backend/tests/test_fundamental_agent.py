import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from app.agents.fundamental import FundamentalAnalystAgent
from app.schemas.agent_signal import AgentSignal
from app.schemas.market_data import NormalizedNews, NormalizedSentiment

@pytest.fixture
def mock_ai_provider():
    return AsyncMock()

@pytest.fixture
def sample_news():
    return [
        NormalizedNews(
            title="BTC ETF Approval Expected",
            source="CryptoNews",
            timestamp=datetime.now(),
            url="https://test.com",
            importance="high",
            sentiment_score=0.8
        )
    ]

@pytest.fixture
def sample_onchain():
    return NormalizedSentiment(
        source="onchain_summary",
        score=0.7,
        classification="bullish",
        timestamp=datetime.now()
    )

@pytest.mark.asyncio
async def test_fundamental_agent_analyze_success(mock_ai_provider, sample_news, sample_onchain):
    """Test fundamental analysis flow with AI mock."""
    agent = FundamentalAnalystAgent(ai_provider=mock_ai_provider)
    
    # Mock AI Response
    mock_ai_response = MagicMock()
    mock_ai_response.content = '{"signal": "STRONG_BUY", "confidence": 0.9, "reasoning": "Strong news and onchain", "key_factors": ["ETF", "Whales"], "onchain_impact": "bullish", "news_impact": "bullish"}'
    mock_ai_provider.analyze.return_value = mock_ai_response
    
    signal = await agent.analyze("BTC/USDT", sample_news, sample_onchain)
    
    assert isinstance(signal, AgentSignal)
    assert signal.signal == "STRONG_BUY"
    assert signal.confidence == 0.9
    assert signal.agent_name == "fundamental_analyst"
    assert "news_impact" in signal.metadata
    assert signal.metadata["onchain_impact"] == "bullish"
