import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from app.agents.sentiment import SentimentAnalystAgent
from app.schemas.agent_signal import AgentSignal
from app.schemas.market_data import NormalizedSentiment

@pytest.fixture
def mock_ai_provider():
    return AsyncMock()

@pytest.fixture
def sample_composite():
    return NormalizedSentiment(
        source="composite",
        score=75.0,
        classification="Extreme Greed",
        timestamp=datetime.now()
    )

@pytest.fixture
def sample_exchange():
    return {
        "funding_rate": 0.0001,
        "open_interest": 1500000.0
    }

@pytest.mark.asyncio
async def test_sentiment_agent_analyze_success(mock_ai_provider, sample_composite, sample_exchange):
    """Test sentiment analysis flow with AI mock."""
    agent = SentimentAnalystAgent(ai_provider=mock_ai_provider)
    
    # Mock AI Response
    mock_ai_response = MagicMock()
    mock_ai_response.content = '{"signal": "SELL", "confidence": 0.7, "reasoning": "Extreme greed levels, potential reversal", "sentiment_classification": "Greed", "risk_level": "high"}'
    mock_ai_provider.analyze.return_value = mock_ai_response
    
    signal = await agent.analyze("BTC/USDT", sample_composite, sample_exchange)
    
    assert isinstance(signal, AgentSignal)
    assert signal.signal == "SELL"
    assert signal.confidence == 0.7
    assert signal.agent_name == "sentiment_analyst"
    assert "risk_level" in signal.metadata
    assert signal.metadata["composite_score"] == 75.0
