import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.providers.fallback_provider import FallbackProvider
from app.core.ai_provider import AIResponse, ChatMessage

@pytest.fixture
def mock_primary():
    p = MagicMock()
    p.chat = AsyncMock()
    p.analyze = AsyncMock()
    p.embed = AsyncMock()
    p.health_check = AsyncMock()
    return p

@pytest.fixture
def mock_fallback():
    f = MagicMock()
    f.chat = AsyncMock()
    f.analyze = AsyncMock()
    f.embed = AsyncMock()
    f.health_check = AsyncMock()
    return f

@pytest.mark.asyncio
async def test_fallback_logic_chat_success_primary(mock_primary, mock_fallback):
    """Test that FallbackProvider uses primary if it succeeds for chat."""
    provider = FallbackProvider(primary=mock_primary, fallback=mock_fallback)
    
    mock_primary.chat.return_value = AIResponse(content="primary response", model="test", provider="p", usage={})
    
    response = await provider.chat([ChatMessage(role="user", content="hi")])
    
    assert response.content == "primary response"
    mock_primary.chat.assert_called_once()
    mock_fallback.chat.assert_not_called()

@pytest.mark.asyncio
async def test_fallback_logic_chat_switches_on_failure(mock_primary, mock_fallback):
    """Test that FallbackProvider switches to fallback if primary fails for chat."""
    provider = FallbackProvider(primary=mock_primary, fallback=mock_fallback)
    
    mock_primary.chat.side_effect = Exception("Primary failed")
    mock_fallback.chat.return_value = AIResponse(content="fallback response", model="test", provider="f", usage={})
    
    response = await provider.chat([ChatMessage(role="user", content="hi")])
    
    assert response.content == "fallback response"
    mock_primary.chat.assert_called_once()
    mock_fallback.chat.assert_called_once()
    assert provider._using_fallback is True

@pytest.mark.asyncio
async def test_fallback_analyze_logic(mock_primary, mock_fallback):
    """Test analyze switching logic."""
    provider = FallbackProvider(primary=mock_primary, fallback=mock_fallback)
    
    mock_primary.analyze.side_effect = Exception("Primary failed")
    mock_fallback.analyze.return_value = AIResponse(content="fallback analytic", model="test", provider="f", usage={})
    
    response = await provider.analyze("system", "data", "instruction")
    
    assert response.content == "fallback analytic"
    mock_primary.analyze.assert_called_once()
    mock_fallback.analyze.assert_called_once()

@pytest.mark.asyncio
async def test_fallback_embed_logic(mock_primary, mock_fallback):
    """Test embed switching logic."""
    provider = FallbackProvider(primary=mock_primary, fallback=mock_fallback)
    
    mock_primary.embed.side_effect = Exception("Primary failed")
    mock_fallback.embed.return_value = [0.1, 0.2]
    
    response = await provider.embed("text")
    
    assert response == [0.1, 0.2]
    mock_primary.embed.assert_called_once()
    mock_fallback.embed.assert_called_once()

@pytest.mark.asyncio
async def test_fallback_health_check_logic(mock_primary, mock_fallback):
    """Test health_check switching logic."""
    provider = FallbackProvider(primary=mock_primary, fallback=mock_fallback)
    
    # If primary health check fails, try fallback
    mock_primary.health_check.return_value = False
    mock_fallback.health_check.return_value = True
    
    assert await provider.health_check() is True
    mock_primary.health_check.assert_called_once()
    mock_fallback.health_check.assert_called_once()

@pytest.mark.asyncio
async def test_fallback_fails_completely_if_no_fallback(mock_primary):
    """Test that it raises exception if primary fails and no fallback exists."""
    provider = FallbackProvider(primary=mock_primary, fallback=None)
    
    mock_primary.chat.side_effect = Exception("Primary failed")
    
    with pytest.raises(Exception, match="Primary failed"):
        await provider.chat([ChatMessage(role="user", content="hi")])

@pytest.mark.asyncio
async def test_fallback_fails_completely_if_fallback_also_fails(mock_primary, mock_fallback):
    """Test that it raises exception if both primary and fallback fail."""
    provider = FallbackProvider(primary=mock_primary, fallback=mock_fallback)
    
    mock_primary.chat.side_effect = Exception("Primary failed")
    mock_fallback.chat.side_effect = Exception("Fallback failed")
    
    with pytest.raises(Exception, match="Fallback failed"):
        await provider.chat([ChatMessage(role="user", content="hi")])
