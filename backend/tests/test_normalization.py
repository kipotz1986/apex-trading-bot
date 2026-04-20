import pytest
from datetime import datetime
from pydantic import ValidationError
from app.schemas.market_data import NormalizedCandle, NormalizedTicker, NormalizedSentiment, NormalizedNews

def test_normalized_candle_valid():
    """Test valid candle normalization."""
    candle = NormalizedCandle(
        timestamp=datetime.now(),
        open=100.0,
        high=110.0,
        low=90.0,
        close=105.0,
        volume=1000.5
    )
    assert candle.open == 100.0
    assert candle.volume == 1000.5

def test_normalized_candle_invalid_types():
    """Test candle normalization with invalid types."""
    with pytest.raises(ValidationError):
        NormalizedCandle(
            timestamp="invalid_date",
            open="not_a_float",
            high=110.0,
            low=90.0,
            close=105.0,
            volume=1000.5
        )

def test_normalized_ticker_valid():
    """Test valid ticker normalization."""
    ticker = NormalizedTicker(
        symbol="BTC/USDT",
        price=60000.0,
        change_24h=5.5
    )
    assert ticker.symbol == "BTC/USDT"
    assert ticker.volume_24h is None

def test_normalized_sentiment_valid():
    """Test valid sentiment normalization."""
    sentiment = NormalizedSentiment(
        source="fear_and_greed",
        score=75.5,
        classification="Greed",
        timestamp=datetime.now()
    )
    assert sentiment.score == 75.5

def test_normalized_sentiment_invalid():
    """Test sentiment normalization with invalid types."""
    with pytest.raises(ValidationError):
        NormalizedSentiment(
            source="fear_and_greed",
            score="not_a_number",
            classification="Greed",
            timestamp=datetime.now()
        )

def test_normalized_news_valid():
    """Test valid news normalization."""
    news = NormalizedNews(
        title="Bitcoin hits ATH",
        source="coindesk",
        timestamp=datetime.now(),
        importance="high",
        currencies=["BTC"]
    )
    assert news.title == "Bitcoin hits ATH"
    assert "BTC" in news.currencies
