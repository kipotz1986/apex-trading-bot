"""
Integration Test - Paper Trading & Mode Switcher.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.paper_trading import PaperTradingEngine
from app.services.mode_switch import ModeSwitcher
from app.models.risk_state import RiskState
from app.models.order import Order
from app.core.database import Base

@pytest.fixture
def db_session():
    # Use SQLite in-memory for tests
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()

def test_paper_order_execution(db_session):
    paper = PaperTradingEngine(db_session)
    
    # Execute a buy order
    order = pytest.mark.asyncio(paper.execute_virtual_order(
        symbol="BTC/USDT",
        side="BUY",
        amount=1.0,
        price=50000.0,
        leverage=1,
        reasoning="Testing paper engine"
    ))
    
    # Manually run if not using pytest-asyncio
    import asyncio
    order = asyncio.run(paper.execute_virtual_order(
        symbol="BTC/USDT", side="BUY", amount=1.0, price=50000.0
    ))
    
    assert order.is_paper is True
    assert order.status == "FILLED"
    assert order.average_filled_price > 50000.0 # Slippage
    assert order.fee_usd > 0

def test_mode_switch_lockdown(db_session):
    # Setup fresh RiskState
    db_session.query(RiskState).delete()
    state = RiskState(
        paper_trading_started_at=datetime.utcnow() - timedelta(days=5), # Only 5 days ago
        is_live_enabled=False
    )
    db_session.add(state)
    db_session.commit()
    
    switcher = ModeSwitcher(db_session)
    
    allowed, message = switcher.can_switch_to_live()
    
    assert allowed is False
    assert "14 hari" in message

def test_mode_switch_success_gate(db_session):
    # Setup RiskState with 15 days
    db_session.query(RiskState).delete()
    state = RiskState(
        paper_trading_started_at=datetime.utcnow() - timedelta(days=15),
        is_live_enabled=False
    )
    db_session.add(state)
    
    # Setup some winning trades
    db_session.query(Order).delete()
    for i in range(10):
        o = Order(
            symbol="BTC/USDT", side="BUY", is_paper=True, 
            status="CLOSED", pnl_usd=100.0, average_filled_price=50000
        )
        db_session.add(o)
    
    db_session.commit()
    
    switcher = ModeSwitcher(db_session)
    allowed, message = switcher.can_switch_to_live()
    
    assert allowed is True
    assert "terpenuhi" in message
