import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.risk_manager import RiskManagerAgent
from app.schemas.portfolio import PortfolioState, Position, RiskDecision

@pytest.fixture
def mock_ai_provider():
    return AsyncMock()

@pytest.fixture
def healthy_portfolio():
    return PortfolioState(
        total_balance=10000.0,
        total_equity=10050.0,
        available_margin=9000.0,
        open_positions=[
            Position(
                symbol="BTC/USDT",
                side="LONG",
                size=0.01,
                entry_price=60000.0,
                current_price=61000.0,
                unrealized_pnl=10.0
            )
        ],
        daily_pnl_pct=0.01,
        weekly_pnl_pct=0.05,
        max_drawdown_pct=-0.02
    )

@pytest.fixture
def failing_portfolio():
    return PortfolioState(
        total_balance=10000.0,
        total_equity=8000.0,
        available_margin=5000.0,
        open_positions=[],
        daily_pnl_pct=-0.04, # Melampaui limit 3%
        weekly_pnl_pct=-0.10,
        max_drawdown_pct=-0.20 # Melampaui limit 15%
    )

@pytest.mark.asyncio
async def test_risk_manager_hard_rule_daily_loss(mock_ai_provider, failing_portfolio):
    """Test hard rules triggered before AI."""
    agent = RiskManagerAgent(ai_provider=mock_ai_provider)
    
    decision = await agent.analyze("ETH/USDT", "BUY", 500.0, failing_portfolio)
    
    assert decision.decision == "REJECT"
    assert "Daily loss limit reached" in decision.reasoning
    # AI should NOT have been called
    mock_ai_provider.analyze.assert_not_called()

@pytest.mark.asyncio
async def test_risk_manager_approve_flow(mock_ai_provider, healthy_portfolio):
    """Test approval flow with AI reasoning."""
    agent = RiskManagerAgent(ai_provider=mock_ai_provider)
    
    # Mock AI Response
    mock_ai_response = MagicMock()
    mock_ai_response.content = '{"decision": "APPROVE", "max_position_size_usd": 500.0, "max_leverage": 5, "reasoning": "Portfolio is healthy, size is small.", "risk_metrics": {"is_within_limits": true}}'
    mock_ai_provider.analyze.return_value = mock_ai_response
    
    decision = await agent.analyze("ETH/USDT", "BUY", 500.0, healthy_portfolio)
    
    assert decision.decision == "APPROVE"
    assert decision.max_position_size_usd == 500.0
    mock_ai_provider.analyze.assert_called_once()

@pytest.mark.asyncio
async def test_risk_manager_auto_cap_size(mock_ai_provider, healthy_portfolio):
    """Test that AI cannot exceed hard size caps (5%)."""
    agent = RiskManagerAgent(ai_provider=mock_ai_provider)
    
    # Mock AI trying to approve 10% size ($1000)
    mock_ai_response = MagicMock()
    mock_ai_response.content = '{"decision": "APPROVE", "max_position_size_usd": 1000.0, "max_leverage": 5, "reasoning": "Looks good!", "risk_metrics": {}}'
    mock_ai_provider.analyze.return_value = mock_ai_response
    
    decision = await agent.analyze("ETH/USDT", "BUY", 1000.0, healthy_portfolio)
    
    # 5% of 10050.0 is 502.5
    assert decision.decision == "REDUCE_SIZE"
    assert decision.max_position_size_usd <= 502.5
    assert "capped at 5% equity" in decision.reasoning
