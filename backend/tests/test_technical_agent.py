import sys
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

# Mock pandas_ta BEFORE importing the agent to prevent ModuleNotFoundError
sys.modules["pandas_ta"] = MagicMock()

import pandas as pd
from app.agents.technical import TechnicalAnalystAgent
from app.schemas.agent_signal import AgentSignal

@pytest.fixture
def mock_ai_provider():
    return AsyncMock()

@pytest.fixture
def sample_candles():
    return [
        {"timestamp": i, "open": 60000 + i, "high": 61000 + i, "low": 59000 + i, "close": 60500 + i, "volume": 100}
        for i in range(100) # Pastikan cukup data (min 50)
    ]

@pytest.mark.asyncio
async def test_technical_agent_analyze_success(mock_ai_provider, sample_candles):
    """Test full analysis flow with AI mock."""
    agent = TechnicalAnalystAgent(ai_provider=mock_ai_provider)
    
    # Mock AI Response
    mock_ai_response = MagicMock()
    mock_ai_response.content = '{"signal": "BUY", "confidence": 0.8, "reasoning": "Test reasoning", "key_levels": {"support": [60000], "resistance": [62000]}, "indicators_summary": {"trend": "bullish", "momentum": "bullish", "volatility": "normal"}, "alignment": {"is_aligned": true, "details": "All good"}}'
    mock_ai_provider.analyze.return_value = mock_ai_response
    
    # Mock pandas_ta to avoid import error if not installed
    with patch('pandas_ta.rsi', return_value=pd.Series([45.0]*100)), \
         patch('pandas_ta.macd', return_value=pd.DataFrame({"MACD": [0.1]*100, "MACDs": [0.05]*100, "MACDh": [0.05]*100})), \
         patch('pandas_ta.bbands', return_value=pd.DataFrame({"BBL": [59000]*100, "BBM": [60000]*100, "BBU": [61000]*100})), \
         patch('pandas_ta.ema', return_value=pd.Series([60000.0]*100)), \
         patch('pandas_ta.atr', return_value=pd.Series([500.0]*100)), \
         patch('pandas_ta.ichimoku', return_value=(pd.DataFrame({"T": [60000]*100, "K": [59500]*100}), pd.DataFrame({"A": [60100]*100, "B": [60200]*100}))):
        
        candles_by_timeframe = {"1h": sample_candles}
        signal = await agent.analyze("BTC/USDT", candles_by_timeframe)
        
        assert isinstance(signal, AgentSignal)
        assert signal.signal == "BUY"
        assert signal.confidence == 0.8
        assert signal.agent_name == "technical_analyst"
        assert "indicators" in signal.metadata
        assert "1h" in signal.metadata["indicators"]

def test_calculate_indicators_logic():
    """Test indicator calculation logic (structure)."""
    # Mocking pandas_ta in this test too
    with patch('pandas_ta.rsi', return_value=pd.Series([45.0]*100)), \
         patch('pandas_ta.macd', return_value=pd.DataFrame({"MACD": [0.1]*100, "MACDs": [0.05]*100, "MACDh": [0.05]*100})), \
         patch('pandas_ta.bbands', return_value=pd.DataFrame({"BBL": [59000]*100, "BBM": [60000]*100, "BBU": [61000]*100})), \
         patch('pandas_ta.ema', return_value=pd.Series([60000.0]*100)), \
         patch('pandas_ta.atr', return_value=pd.Series([500.0]*100)), \
         patch('pandas_ta.ichimoku', return_value=(pd.DataFrame({"T": [60000]*100, "K": [59500]*100}), pd.DataFrame({"A": [60100]*100, "B": [60200]*100}))):
             
        agent = TechnicalAnalystAgent(ai_provider=None)
        df = pd.DataFrame([
            {"open": 60000, "high": 61000, "low": 59000, "close": 60500, "volume": 100}
            for _ in range(100)
        ])
        
        indicators = agent.calculate_indicators(df)
        
        assert "rsi" in indicators
        assert "macd" in indicators
        assert "bollinger" in indicators
        assert "ema_50" in indicators
        assert "volume" in indicators
        assert indicators["volume"]["above_average"] is False

def test_detect_tf_alignment_logic():
    """Test the alignment detection algorithm."""
    agent = TechnicalAnalystAgent(ai_provider=None)
    
    # Case 1: All bullish
    all_indicators = {
        "1h": {"ema_50": 50000, "current_price": 60000},
        "4h": {"ema_50": 50000, "current_price": 60000}
    }
    alignment = agent._detect_tf_alignment(all_indicators)
    assert alignment["is_aligned"] is True
    assert "bullish" in alignment["details"].lower()
    
    # Case 2: Conflicting
    all_indicators = {
        "1h": {"ema_50": 70000, "current_price": 60000},
        "4h": {"ema_50": 50000, "current_price": 60000}
    }
    alignment = agent._detect_tf_alignment(all_indicators)
    assert alignment["is_aligned"] is False
    assert "1h: bearish" in alignment["details"]
