import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.onchain_data import OnChainDataService

@pytest.mark.asyncio
async def test_get_whale_movements_success():
    """Test fetching whale movements successfully with mocks."""
    service = OnChainDataService()
    service.whale_key = "test-key"
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "transactions": [
            {"hash": "0x123", "amount": 1000, "symbol": "BTC", "value_usd": 60000000}
        ]
    }
    
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        result = await service.get_whale_movements()
        
        assert len(result) == 1
        assert result[0]["symbol"] == "BTC"
        mock_get.assert_called_once()

@pytest.mark.asyncio
async def test_get_exchange_flows_glassnode_success():
    """Test fetching exchange flows from Glassnode with mocks."""
    service = OnChainDataService()
    service.glassnode_key = "test-key"
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{"t": 12345678, "v": -500.5}] # Net outflow
    
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        result = await service.get_exchange_flows("BTC")
        
        assert result["net_flow"] == -500.5
        assert result["provider"] == "glassnode"

@pytest.mark.asyncio
async def test_get_whale_movements_no_key():
    """Test that it returns empty list if no API key is provided."""
    service = OnChainDataService()
    service.whale_key = ""
    
    result = await service.get_whale_movements()
    assert result == []

@pytest.mark.asyncio
async def test_onchain_summary_aggregation():
    """Test the summary aggregation logic."""
    service = OnChainDataService()
    
    with patch.object(service, 'get_exchange_flows', new_callable=AsyncMock) as mock_flows, \
         patch.object(service, 'get_whale_movements', new_callable=AsyncMock) as mock_whales:
        
        mock_flows.return_value = {"net_flow": -1000, "provider": "test"} # Bullish
        mock_whales.return_value = [] # Neutral
        
        summary = await service.get_summary("BTC")
        
        assert summary["sentiment_score"] > 0
        assert summary["whale_count"] == 0
