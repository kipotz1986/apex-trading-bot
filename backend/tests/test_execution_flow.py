"""
Integration Test - Full Execution Flow.

Memverifikasi flow dari keputusan Orchestrator hingga eksekusi di ExecutionEngine.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.orchestrator import MasterOrchestrator
from app.services.execution import ExecutionEngine
from app.services.pre_trade_validator import PreTradeValidator
from app.schemas.trade_decision import TradeDecision
from app.schemas.portfolio import PortfolioState
from app.models.order import Order

@pytest.fixture
def mock_execution_setup():
    # Depedencies
    ai = AsyncMock()
    tech = AsyncMock()
    fund = AsyncMock()
    sent = AsyncMock()
    risk = AsyncMock()
    copy = AsyncMock()
    consensus = MagicMock()
    regime_det = MagicMock()
    regime_strat = MagicMock()
    scorer = MagicMock()
    
    # Proper return values for agents to pass Pydantic validation
    from app.schemas.agent_signal import AgentSignal
    mock_sig = AgentSignal(agent_name="test", symbol="BTC/USDT", signal="BUY", confidence=0.8, reasoning="test")
    tech.analyze.return_value = mock_sig
    fund.analyze.return_value = mock_sig
    sent.analyze.return_value = mock_sig
    copy.analyze.return_value = mock_sig
    
    # New Epic 7 dependencies
    executor = AsyncMock(spec=ExecutionEngine)
    validator = AsyncMock(spec=PreTradeValidator)
    
    # DB session
    db = MagicMock()
    
    orchestrator = MasterOrchestrator(
        ai, tech, fund, sent, risk, copy, consensus, 
        regime_det, regime_strat, scorer, executor, validator
    )
    
    return {
        "orchestrator": orchestrator,
        "executor": executor,
        "validator": validator,
        "db": db,
        "risk": risk,
        "consensus": consensus,
        "regime_det": regime_det,
        "regime_strat": regime_strat,
        "mock_sig": mock_sig
    }

@pytest.mark.asyncio
async def test_full_execution_flow_success(mock_execution_setup):
    orchestrator = mock_execution_setup["orchestrator"]
    executor = mock_execution_setup["executor"]
    validator = mock_execution_setup["validator"]
    risk = mock_execution_setup["risk"]
    consensus = mock_execution_setup["consensus"]
    regime_det = mock_execution_setup["regime_det"]
    regime_strat = mock_execution_setup["regime_strat"]
    
    # 1. Mock Consensus & Regime
    consensus.calculate.return_value = {
        "action": "EXECUTE_LONG",
        "score": 0.85,
        "confidence": 0.9,
        "proposed_size": 200.0,
        "reasoning": "Strong consensus",
        "has_conflict": False,
        "leverage": 3,
        "stop_loss": 49000,
        "take_profit": [51000]
    }
    regime_det.detect.return_value = {"regime": "trending_up"}
    regime_strat.adjust_decision.side_effect = lambda d, r: d 
    
    # 2. Mock Risk Manager
    risk.analyze.return_value = MagicMock(
        decision="APPROVE", max_position_size_usd=200.0, max_leverage=3
    )
    
    # 3. Mock Validator
    validator.validate.return_value = (True, "")
    
    # 4. Mock Executor
    executor.open_position.return_value = MagicMock(exchange_order_id="TEST_ORD_123")
    
    # Setup market data and portfolio
    portfolio = PortfolioState(
        total_balance=1000, total_equity=1000, available_margin=1000,
        daily_pnl_pct=0, weekly_pnl_pct=0, max_drawdown_pct=0
    )
    market_data = {
        "candles": [{"close": 50000} for _ in range(10)],
        "regime": "trending_up"
    }
    
    # ACT
    decision = await orchestrator.decide("BTC/USDT", market_data, portfolio)
    
    # ASSERT
    assert "EXECUTED ID: TEST_ORD_123" in decision.reasoning
    executor.open_position.assert_called_once()
    # Check amount: 200 / 50000 = 0.004
    args, kwargs = executor.open_position.call_args
    assert kwargs["amount"] == 0.004
    assert kwargs["side"] == "BUY"

@pytest.mark.asyncio
async def test_execution_blocked_by_validation(mock_execution_setup):
    orchestrator = mock_execution_setup["orchestrator"]
    validator = mock_execution_setup["validator"]
    executor = mock_execution_setup["executor"]
    consensus = mock_execution_setup["consensus"]
    regime_det = mock_execution_setup["regime_det"]
    regime_strat = mock_execution_setup["regime_strat"]
    risk = mock_execution_setup["risk"]
    
    # Mock mocks
    regime_det.detect.return_value = {"regime": "sideways"}
    regime_strat.adjust_decision.side_effect = lambda d, r: d
    risk.analyze.return_value = MagicMock(
        decision="APPROVE", max_position_size_usd=100.0, max_leverage=1
    )
    
    # Mock consensus success
    consensus.calculate.return_value = {
        "action": "EXECUTE_LONG", 
        "score": 0.8, 
        "confidence": 0.8, 
        "proposed_size": 100,
        "reasoning": "Test reasoning"
    }
    
    # Mock Validator REJECTION
    validator.validate.return_value = (False, "Insufficient balance")
    
    portfolio = PortfolioState(
        total_balance=100, total_equity=100, available_margin=50,
        daily_pnl_pct=0, weekly_pnl_pct=0, max_drawdown_pct=0
    )
    market_data = {"candles": [{"close": 50000}]}
    
    decision = await orchestrator.decide("BTC/USDT", market_data, portfolio)
    
    assert decision.action == "HOLD"
    assert "PRE-TRADE VALIDATION FAILED" in decision.reasoning
    executor.open_position.assert_not_called()
