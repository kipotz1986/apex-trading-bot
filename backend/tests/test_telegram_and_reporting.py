"""
Integration Test - Telegram Notification & Reporting.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.telegram import TelegramService
from app.services.report_composer import ReportComposer
from app.models.risk_state import RiskState
from app.models.order import Order
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.risk_state import Base

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    # Setup initial risk state
    rs = RiskState(current_equity=10000.0, equity_peak=10000.0, system_status="NORMAL")
    db.add(rs)
    db.commit()
    
    yield db
    db.close()

@pytest.mark.asyncio
async def test_telegram_send_message():
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200, 
            json=lambda: {"ok": True}
        )
        
        # We need to mock settings before initialising TelegramService
        with patch("app.services.telegram.settings") as mock_settings:
            mock_settings.TELEGRAM_BOT_TOKEN = "test_token"
            mock_settings.TELEGRAM_CHAT_ID = "12345"
            
            telegram = TelegramService()
            success = await telegram.send_message("Test message")
            
            assert success is True
            mock_post.assert_called_once()
            
            await telegram.close()

@pytest.mark.asyncio
async def test_report_composition(db_session):
    # Add some mock trades
    trade = Order(
        symbol="BTC/USDT", side="BUY", status="CLOSED", 
        pnl_usd=250.0, closed_at=datetime.utcnow()
    )
    db_session.add(trade)
    db_session.commit()
    
    composer = ReportComposer(db_session)
    report = await composer.compose_daily_report()
    
    assert "APEX Daily Report" in report
    assert "$250.00" in report
    assert "BTC/USDT" in report

@pytest.mark.asyncio
async def test_telegram_alert_formatting():
    with patch("app.services.telegram.TelegramService.send_message", new_callable=AsyncMock) as mock_send:
        # Mock settings
        with patch("app.services.telegram.settings") as mock_settings:
            mock_settings.TELEGRAM_BOT_TOKEN = "test_token"
            mock_settings.TELEGRAM_CHAT_ID = "12345"
            
            telegram = TelegramService()
            await telegram.send_alert("critical", "CRASH", "Market is dump")
            
            args, _ = mock_send.call_args
            assert "🔴" in args[0]
            assert "CRASH" in args[0]
            assert "Market is dump" in args[0]
            
            await telegram.close()

# Need to import datetime for the test
from datetime import datetime
