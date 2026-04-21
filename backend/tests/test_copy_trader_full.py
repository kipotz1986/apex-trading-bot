"""
Integration Test - Copy Trading Agent & Services.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.copy_trader import CopyTradingAgent
from app.services.copy_trading.leaderboard import BybitLeaderboardService
from app.services.copy_trading.trader_filter import TraderFilter
from app.services.copy_trading.position_tracker import PositionTracker
from app.models.copy_trade import TopTrader, CopyTradeEvent
from app.schemas.copy_trading import TraderStats

@pytest.fixture
def mock_db():
    session = MagicMock()
    return session

@pytest.mark.asyncio
async def test_leaderboard_and_filter():
    service = BybitLeaderboardService()
    traders = await service.fetch()
    assert len(traders) > 0
    
    filtrator = TraderFilter()
    top_traders = filtrator.filter_and_score(traders)
    
    # "HighLevGambler" (T003) should be filtered out due to drawdown (65% > 25%)
    trader_ids = [t["trader_id"] for t in top_traders]
    assert "T003" not in trader_ids
    assert "T001" in trader_ids # DiamondHands should pass

@pytest.mark.asyncio
async def test_agent_aggregation_logic(mock_db):
    # Mock active traders
    mock_db.query.return_value.filter.return_value.all.side_effect = [
        [MagicMock(trader_id="T001"), MagicMock(trader_id="T002"), MagicMock(trader_id="T003")], # active_trader_ids
        [
            MagicMock(trader_id="T001", side="BUY", event_type="OPEN"),
            MagicMock(trader_id="T002", side="BUY", event_type="OPEN"),
            MagicMock(trader_id="T003", side="BUY", event_type="OPEN")
        ] # events
    ]
    
    agent = CopyTradingAgent(db=mock_db)
    signal = await agent.analyze("BTC/USDT")
    
    assert signal.signal == "BUY"
    assert signal.confidence >= 0.5
    assert "3 dari top traders" in signal.reasoning

@pytest.mark.asyncio
async def test_agent_neutral_logic(mock_db):
    # Mock only 2 traders
    mock_db.query.return_value.filter.return_value.all.side_effect = [
        [MagicMock(trader_id="T001"), MagicMock(trader_id="T002")],
        [
            MagicMock(trader_id="T001", side="BUY", event_type="OPEN"),
            MagicMock(trader_id="T002", side="BUY", event_type="OPEN"),
        ]
    ]
    
    agent = CopyTradingAgent(db=mock_db)
    signal = await agent.analyze("BTC/USDT")
    
    assert signal.signal == "NEUTRAL"
    assert "Tidak ada konsensus yang cukup" in signal.reasoning
