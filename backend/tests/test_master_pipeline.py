"""
Integration Test - Master Orchestrator Pipeline.

Memverifikasi flow end-to-end dari data pasar hingga keputusan final.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.orchestrator import MasterOrchestrator
from app.agents.technical import TechnicalAnalystAgent
from app.agents.fundamental import FundamentalAnalystAgent
from app.agents.sentiment import SentimentAnalystAgent
from app.agents.risk_manager import RiskManagerAgent
from app.agents.copy_trader import CopyTradingAgent
from app.services.consensus import ConsensusEngine
from app.services.regime_detector import RegimeDetector
from app.services.regime_strategy import RegimeStrategy
from app.services.agent_scorer import AgentScorer
from app.schemas.agent_signal import AgentSignal
from app.schemas.portfolio import PortfolioState
from app.schemas.portfolio import RiskDecision

@pytest.fixture
def mock_all():
    ai = AsyncMock()
    # Mock return AI untuk Judge (Debate)
    ai.analyze.return_value = MagicMock(content='{"action": "EXECUTE_LONG", "confidence": 0.9, "reasoning": "Judge supports Long"}')
    
    tech = AsyncMock(spec=TechnicalAnalystAgent)
    fund = AsyncMock(spec=FundamentalAnalystAgent)
    sent = AsyncMock(spec=SentimentAnalystAgent)
    risk = AsyncMock(spec=RiskManagerAgent)
    copy = AsyncMock(spec=CopyTradingAgent)
    
    # Mocking basic behavior
    tech.analyze.return_value = AgentSignal(agent_name="technical", symbol="BTC/USDT", signal="BUY", confidence=0.9, reasoning="MA Cross")
    fund.analyze.return_value = AgentSignal(agent_name="fundamental", symbol="BTC/USDT", signal="BUY", confidence=0.9, reasoning="ETF Inflow")
    sent.analyze.return_value = AgentSignal(agent_name="sentiment", symbol="BTC/USDT", signal="BUY", confidence=0.8, reasoning="Sentiment is high")
    copy.analyze.return_value = AgentSignal(agent_name="copy_trader", symbol="BTC/USDT", signal="BUY", confidence=0.8, reasoning="Follow the whales")
    
    risk.analyze.return_value = RiskDecision(decision="APPROVE", max_position_size_usd=100.0, max_leverage=3, reasoning="Risk is fine")
    
    db = MagicMock() # Mock DB session
    scorer = MagicMock(spec=AgentScorer)
    scorer.get_weights.return_value = {"technical": 0.3, "fundamental": 0.25, "sentiment": 0.2, "copy_trader": 0.25}
    
    consensus = ConsensusEngine()
    regime_det = RegimeDetector()
    regime_strat = RegimeStrategy()
    
    orchestrator = MasterOrchestrator(
        ai, tech, fund, sent, risk, copy, consensus, regime_det, regime_strat, scorer
    )
    
    return {
        "orchestrator": orchestrator,
        "tech": tech,
        "fund": fund,
        "sent": sent,
        "risk": risk
    }

@pytest.mark.asyncio
async def test_pipeline_unanimous_buy(mock_all):
    orchestrator = mock_all["orchestrator"]
    
    portfolio = PortfolioState(
        total_balance=1000, 
        total_equity=1000, 
        available_margin=1000,
        daily_pnl_pct=0,
        weekly_pnl_pct=0,
        max_drawdown_pct=0
    )
    market_data = {"candles": [{"close": 60000} for _ in range(100)], "news": [], "regime": "trending_up"}
    
    decision = await orchestrator.decide("BTC/USDT", market_data, portfolio)
    
    assert decision.action == "EXECUTE_LONG"
    assert decision.position_size_usd > 0
    assert "technical" in decision.agent_signals

@pytest.mark.asyncio
async def test_pipeline_risk_veto(mock_all):
    orchestrator = mock_all["orchestrator"]
    risk = mock_all["risk"]
    
    # Mock Risk Manager rejecting the trade
    risk.analyze.return_value = RiskDecision(decision="REJECT", max_position_size_usd=0, max_leverage=1, reasoning="Drawdown too high")
    
    portfolio = PortfolioState(
        total_balance=1000, 
        total_equity=1000, 
        available_margin=1000,
        daily_pnl_pct=0,
        weekly_pnl_pct=0,
        max_drawdown_pct=0
    )
    market_data = {"candles": [{"close": 60000} for _ in range(100)]}
    
    decision = await orchestrator.decide("BTC/USDT", market_data, portfolio)
    
    assert decision.action == "HOLD"
    assert "REJECTED BY RISK MANAGER" in decision.reasoning

@pytest.mark.asyncio
async def test_pipeline_high_volatility_threshold(mock_all):
    orchestrator = mock_all["orchestrator"]
    
    # Mock signals slightly bullish but not strong enough for 90% threshold of high_volatility
    # Score 0.4 * 0.5 (weight avg) = 0.2 approx
    mock_all["tech"].analyze.return_value = AgentSignal(agent_name="technical", symbol="BTC/USDT", signal="BUY", confidence=0.3, reasoning="weak")
    
    # Mock High Volatility Regime
    with MagicMock() as mock_rd:
        mock_rd.detect.return_value = {"regime": "high_volatility", "confidence": 1.0, "metrics": {}}
        orchestrator.regime_detector = mock_rd
        
        portfolio = PortfolioState(
        total_balance=1000, 
        total_equity=1000, 
        available_margin=1000,
        daily_pnl_pct=0,
        weekly_pnl_pct=0,
        max_drawdown_pct=0
    )
        market_data = {"candles": []}
        
        decision = await orchestrator.decide("BTC/USDT", market_data, portfolio)
        
        # High volatility requires 90% confidence, so it should HOLD
        assert decision.action == "HOLD"
        assert "high_volatility" in decision.reasoning.lower()
