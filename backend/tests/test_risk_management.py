"""
Integration Test - Risk Management & Circuit Breakers.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from app.services.risk.circuit_breaker import CircuitBreaker
from app.services.risk.risk_guard import RiskGuard
from app.models.risk_state import RiskState
from app.models.order import Order
from app.schemas.portfolio import PortfolioState
from app.schemas.trade_decision import TradeDecision

@pytest.fixture
def mock_db():
    session = MagicMock()
    # Mocking first() to return a RiskState
    state = RiskState(equity_peak=10000.0, system_status="NORMAL", consecutive_losses=0)
    session.query.return_value.first.return_value = state
    return session, state

@pytest.mark.asyncio
async def test_drawdown_circuit_breaker(mock_db):
    db, state = mock_db
    cb = CircuitBreaker(db)
    
    # 15% of 10000 is 8500 or below
    # Trigger with 8000 equity
    triggered, reason = await cb.check_all(current_equity=8000.0)
    
    assert triggered is True
    assert "Max drawdown reached" in reason
    assert state.system_status == "EMERGENCY_STOP"

def test_position_sizing_logic(mock_db):
    db, state = mock_db
    guard = RiskGuard(db)
    
    # Mock current exposure to 0
    db.query.return_value.filter.return_value.all.return_value = []
    
    # 5% of 10000 is 500
    # Try to open 1000
    import asyncio
    safe_size = asyncio.run(guard.calculate_safe_size(proposed_size_usd=1000.0, current_equity=10000.0))
    
    assert safe_size == 500.0

def test_consecutive_loss_multiplier(mock_db):
    db, state = mock_db
    state.consecutive_losses = 5
    guard = RiskGuard(db)
    
    # Equity 10000 -> 5% = 500. Multiplier 0.5 -> 250
    import asyncio
    safe_size = asyncio.run(guard.calculate_safe_size(proposed_size_usd=1000.0, current_equity=10000.0))
    
    assert safe_size == 250.0

def test_correlation_guard(mock_db):
    db, state = mock_db
    guard = RiskGuard(db)
    
    # Mock that BTC is already open
    db.query.return_value.filter.return_value.all.return_value = [("BTC/USDT",)]
    
    # Check ETH (Highly correlated)
    is_valid = guard.validate_correlation("ETH/USDT", "BUY")
    assert is_valid is False
    
    # Check some random alt (Not in correlation group)
    is_valid = guard.validate_correlation("LINK/USDT", "BUY")
    assert is_valid is True
