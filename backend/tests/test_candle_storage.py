import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from app.services.candle_storage import CandleStorageService
from app.models.candle import Candle

@pytest.fixture
def mock_db():
    db = MagicMock()
    return db

@pytest.fixture
def storage_service(mock_db):
    return CandleStorageService(db=mock_db)

@pytest.mark.asyncio
async def test_save_candles_empty(storage_service):
    """Test saving empty list of candles."""
    result = await storage_service.save_candles("BTC/USDT", "1h", [])
    assert result == 0
    storage_service.db.execute.assert_not_called()

@pytest.mark.asyncio
async def test_save_candles_success(storage_service):
    """Test saving candles successfully (verifying db calls)."""
    candles = [
        {
            "timestamp": datetime(2024, 1, 1, 0, 0),
            "open": 40000.0,
            "high": 41000.0,
            "low": 39000.0,
            "close": 40500.0,
            "volume": 10.5
        }
    ]
    
    # Mocking postgres-specific insert statement logic is hard,
    # so we just verify that commit was called and execute didn't crash.
    result = await storage_service.save_candles("BTC/USDT", "1h", candles)
    
    assert result == 1
    assert storage_service.db.execute.called
    assert storage_service.db.commit.called

def test_get_latest_timestamp(storage_service, mock_db):
    """Test getting the latest timestamp from DB."""
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_order = mock_filter.order_by.return_value
    
    # Mock return value of .first()
    expected_time = datetime(2024, 1, 1, 12, 0)
    mock_order.first.return_value = Candle(timestamp=expected_time)
    
    result = storage_service.get_latest_timestamp("BTC/USDT", "1h")
    
    assert result == expected_time
    mock_db.query.assert_called_with(Candle)

def test_get_latest_timestamp_none(storage_service, mock_db):
    """Test getting latest timestamp when no data exists."""
    mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    
    result = storage_service.get_latest_timestamp("BTC/USDT", "1h")
    assert result is None
