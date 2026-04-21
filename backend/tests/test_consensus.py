"""
Unit tests for Consensus Engine.
"""

import pytest
from app.services.consensus import ConsensusEngine
from app.schemas.agent_signal import AgentSignal

def test_consensus_unanimous_buy():
    engine = ConsensusEngine()
    signals = {
        "technical": AgentSignal(agent_name="technical", symbol="BTC/USDT", signal="BUY", confidence=1.0, reasoning="test"),
        "fundamental": AgentSignal(agent_name="fundamental", symbol="BTC/USDT", signal="BUY", confidence=1.0, reasoning="test"),
        "sentiment": AgentSignal(agent_name="sentiment", symbol="BTC/USDT", signal="BUY", confidence=1.0, reasoning="test"),
        "copy_trader": AgentSignal(agent_name="copy_trader", symbol="BTC/USDT", signal="BUY", confidence=1.0, reasoning="test")
    }
    
    result = engine.calculate(signals)
    assert result["action"] == "EXECUTE_LONG"
    assert result["score"] == 0.5 # Σ (0.5 * 1.0 * weight) version weights = 0.5 * 1.0 * (0.3+0.25+0.2+0.25) = 0.5
    assert result["has_conflict"] is False

def test_consensus_conflict():
    engine = ConsensusEngine()
    signals = {
        "technical": AgentSignal(agent_name="technical", symbol="BTC/USDT", signal="STRONG_BUY", confidence=1.0, reasoning="test"),
        "fundamental": AgentSignal(agent_name="fundamental", symbol="BTC/USDT", signal="STRONG_SELL", confidence=1.0, reasoning="test")
    }
    
    result = engine.calculate(signals)
    assert result["has_conflict"] is True
    assert "konflik" in result["reasoning"].lower()

def test_consensus_hold_on_weak_signals():
    engine = ConsensusEngine()
    signals = {
        "technical": AgentSignal(agent_name="technical", symbol="BTC/USDT", signal="BUY", confidence=0.4, reasoning="test"),
        "sentiment": AgentSignal(agent_name="sentiment", symbol="BTC/USDT", signal="NEUTRAL", confidence=1.0, reasoning="test")
    }
    
    result = engine.calculate(signals)
    assert result["action"] == "HOLD"
    assert result["score"] < 0.4
