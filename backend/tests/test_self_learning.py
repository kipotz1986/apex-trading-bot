"""
Integration Test - Self-Learning & Pattern Memory.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock
from app.services.learning.state_space import StateSpace
from app.services.learning.pattern_memory import PatternMemory
from app.services.learning.reward import RewardFunction
from app.schemas.portfolio import PortfolioState

@pytest.fixture
def mock_learning_setup():
    # StateSpace
    ss = StateSpace(feature_dim=25)
    
    # PatternMemory (using in-memory/temp for testing)
    import tempfile
    temp_dir = tempfile.mkdtemp()
    pm = PatternMemory(persist_directory=temp_dir)
    
    return ss, pm

def test_reward_calculation():
    reward_service = RewardFunction()
    
    # scenario: Win with SL
    win_result = {
        "pnl_pct": 2.5,
        "max_drawdown_during_trade": 0.5,
        "had_sl": True,
        "hold_time_minutes": 60
    }
    reward = reward_service.calculate(win_result)
    assert reward > 2.5 # pnl + sl bonus
    
    # scenario: Loss with overtrading
    loss_result = {
        "pnl_pct": -1.5,
        "max_drawdown_during_trade": 3.0,
        "had_sl": True,
        "hold_time_minutes": 2
    }
    reward = reward_service.calculate(loss_result)
    assert reward < -1.5 # pnl + mdd penalty + overtrading penalty

def test_state_vector_shape():
    ss = StateSpace(feature_dim=25)
    portfolio = PortfolioState(
        total_balance=10000, total_equity=10000, available_margin=5000,
        daily_pnl_pct=0, weekly_pnl_pct=0, max_drawdown_pct=0
    )
    market_data = {"candles": [{"close": 50000} for _ in range(10)], "fear_greed_index": 45}
    agent_signals = {"technical": MagicMock(signal="BUY", confidence=0.8)}
    
    vector = ss.build_vector(market_data, portfolio, agent_signals)
    assert vector.shape == (25,)
    assert isinstance(vector, np.ndarray)

def test_pattern_memory_storage_and_retrieval(mock_learning_setup):
    ss, pm = mock_learning_setup
    
    # 1. Store a "bullish" pattern
    vec_bullish = [0.1] * 25
    pm.store_pattern(vec_bullish, {"outcome": "WIN", "pnl": 2.0}, "p1")
    pm.store_pattern(vec_bullish, {"outcome": "WIN", "pnl": 1.5}, "p2")
    pm.store_pattern([0.11] * 25, {"outcome": "WIN", "pnl": 3.0}, "p3")
    
    # 2. Query similar
    query_vec = [0.105] * 25
    experience = pm.get_market_experience(query_vec)
    
    assert experience["sample_size"] == 3
    assert experience["win_rate"] == 1.0
    assert experience["average_pnl"] > 1.5
