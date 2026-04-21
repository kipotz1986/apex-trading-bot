import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.onchain_data import OnChainDataService


@pytest.mark.asyncio
async def test_get_global_market_success():
    """Test fetching global market metrics from CoinGecko."""
    service = OnChainDataService()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {
            "total_market_cap": {"usd": 2500000000000},
            "total_volume": {"usd": 100000000000},
            "market_cap_percentage": {"btc": 52.5},
            "active_cryptocurrencies": 15000,
            "market_cap_change_percentage_24h_usd": 2.5,
        }
    }

    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        result = await service.get_global_market()

        assert result["btc_dominance"] == 52.5
        assert result["total_market_cap_usd"] == 2500000000000
        assert result["market_cap_change_24h_pct"] == 2.5


@pytest.mark.asyncio
async def test_get_btc_onchain_stats_success():
    """Test fetching BTC on-chain stats from Blockchain.com."""
    service = OnChainDataService()

    mock_stats = MagicMock()
    mock_stats.status_code = 200
    mock_stats.json.return_value = {
        "hash_rate": 500000000,
        "difficulty": 72000000000000,
        "n_blocks_total": 850000,
        "minutes_between_blocks": 9.5,
    }

    mock_unconf = MagicMock()
    mock_unconf.status_code = 200
    mock_unconf.text = "75000"

    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [mock_stats, mock_unconf]

        result = await service.get_btc_onchain_stats()

        assert result["hash_rate"] == 500000000
        assert result["unconfirmed_txs"] == 75000


@pytest.mark.asyncio
async def test_get_eth_large_transfers_no_key():
    """Test that ETH transfers returns empty if no Etherscan key."""
    service = OnChainDataService()
    service.etherscan_key = ""

    result = await service.get_eth_large_transfers()
    assert result == []


@pytest.mark.asyncio
async def test_get_summary_aggregation():
    """Test the summary aggregation logic using mocks."""
    service = OnChainDataService()

    with patch.object(service, 'get_global_market', new_callable=AsyncMock) as mock_global, \
         patch.object(service, 'get_btc_onchain_stats', new_callable=AsyncMock) as mock_btc:

        # Scenario: Market cap up 5%, BTC dom 52%, mempool busy
        mock_global.return_value = {
            "market_cap_change_24h_pct": 5.0,
            "btc_dominance": 52.0,
        }
        mock_btc.return_value = {
            "unconfirmed_txs": 120000,
        }

        summary = await service.get_summary("BTC")

        # mc_change > 3 => +25, btc_dom 52 (40-55) => 0, unconf > 100k => +10
        assert summary.score == 35
        assert summary.classification == "Bullish"
        assert summary.source == "onchain_free"


@pytest.mark.asyncio
async def test_get_trending_coins_success():
    """Test fetching trending coins from CoinGecko."""
    service = OnChainDataService()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "coins": [
            {"item": {"name": "Bitcoin", "symbol": "BTC", "market_cap_rank": 1, "score": 0}},
            {"item": {"name": "Ethereum", "symbol": "ETH", "market_cap_rank": 2, "score": 1}},
        ]
    }

    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        result = await service.get_trending_coins()

        assert len(result) == 2
        assert result[0]["symbol"] == "BTC"
        assert result[1]["name"] == "Ethereum"
