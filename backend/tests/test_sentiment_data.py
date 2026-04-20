import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.sentiment_data import SentimentDataService

@pytest.fixture
def mock_exchange_service():
    service = MagicMock()
    service.exchange = AsyncMock()
    return service

@pytest.mark.asyncio
async def test_get_fear_greed_index_success():
    """Test fetching Fear & Greed Index successfully."""
    service = SentimentDataService(exchange=None)
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [{"value": "75", "value_classification": "Greed"}]
    }
    
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        result = await service.get_fear_greed_index()
        
        assert result["value"] == 75
        assert result["classification"] == "Greed"

@pytest.mark.asyncio
async def test_get_exchange_sentiment_success(mock_exchange_service):
    """Test fetching funding rate and open interest from exchange."""
    service = SentimentDataService(exchange=mock_exchange_service)
    
    mock_exchange_service.exchange.fetch_funding_rate.return_value = {"fundingRate": 0.0001}
    mock_exchange_service.exchange.fetch_open_interest.return_value = {"openInterestAmount": 1000000.0}
    
    result = await service.get_exchange_sentiment("BTC/USDT")
    
    assert result["funding_rate"] == 0.0001
    assert result["open_interest"] == 1000000.0

@pytest.mark.asyncio
async def test_composite_sentiment_calculation(mock_exchange_service):
    """Test the composite score calculation logic."""
    service = SentimentDataService(exchange=mock_exchange_service)
    
    with patch.object(service, 'get_fear_greed_index', new_callable=AsyncMock) as mock_fng, \
         patch.object(service, 'get_exchange_sentiment', new_callable=AsyncMock) as mock_exc:
        
        # Scenario: Greed (75) and High Positive Funding Rate (0.001)
        mock_fng.return_value = {"value": 75, "classification": "Greed"}
        mock_exc.return_value = {"funding_rate": 0.001, "open_interest": 0.0}
        
        result = await service.get_composite_sentiment("BTC/USDT")
        
        # F&G Score: (75-50)*2 = 50
        # FR Score: (0.001*10000)/3 = 3.33
        # Composite: 50*0.7 + 3.33*0.3 = 35 + 1 = 36
        assert result["composite_score"] > 0
        assert result["composite_score"] == 36.0 # (50*0.7) + (3.33*0.3) = 35 + 0.999 = 36.00
