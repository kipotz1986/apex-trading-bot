import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.news_feed import NewsFeedService

@pytest.mark.asyncio
async def test_get_latest_news_success():
    """Test fetching latest news from CryptoPanic successfully."""
    service = NewsFeedService()
    service.api_key = "test-token"
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {
                "title": "BTC hitting new ATH",
                "domain": "coindesk.com",
                "url": "https://example.com/btc",
                "created_at": "2024-05-20T10:00:00Z",
                "votes": {"important": 15, "positive": 50, "negative": 5},
                "currencies": [{"code": "BTC"}]
            }
        ]
    }
    
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        news = await service.get_latest_news(currencies=["BTC"])
        
        assert len(news) == 1
        assert news[0]["title"] == "BTC hitting new ATH"
        assert news[0]["importance"] == "high"
        assert "BTC" in news[0]["currencies"]

@pytest.mark.asyncio
async def test_get_latest_news_no_key():
    """Test that it returns empty list if no API key is provided."""
    service = NewsFeedService()
    service.api_key = ""
    
    news = await service.get_latest_news()
    assert news == []

@pytest.mark.asyncio
async def test_calculate_importance_logic():
    """Test the importance calculation logic."""
    service = NewsFeedService()
    
    # High importance
    assert service._calculate_importance({"votes": {"important": 11, "positive": 0, "negative": 0}}) == "high"
    # Medium importance
    assert service._calculate_importance({"votes": {"important": 1, "positive": 55, "negative": 0}}) == "medium"
    # Low importance
    assert service._calculate_importance({"votes": {"important": 0, "positive": 5, "negative": 0}}) == "low"
