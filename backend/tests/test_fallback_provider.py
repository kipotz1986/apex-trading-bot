import pytest
from unittest.mock import AsyncMock, patch
from app.core.providers.fallback_provider import FallbackProvider
from app.core.ai_provider import AIResponse, ChatMessage

@pytest.mark.asyncio
async def test_fallback_logic_on_failure():
    """Test that FallbackProvider switches to fallback when primary fails."""
    primary = AsyncMock()
    fallback = AsyncMock()
    
    # Setup primary to fail
    primary.chat.side_effect = Exception("Primary failed")
    
    # Setup fallback to succeed
    fallback_response = AIResponse(
        content="Success from fallback",
        model="gemini-pro",
        provider="google"
    )
    fallback.chat.return_value = fallback_response
    
    provider = FallbackProvider(primary=primary, fallback=fallback)
    
    messages = [ChatMessage(role="user", content="Hello")]
    response = await provider.chat(messages)
    
    assert response.content == "Success from fallback"
    assert response.provider == "google"
    assert provider._using_fallback is True
    
    primary.chat.assert_called_once()
    fallback.chat.assert_called_once()

@pytest.mark.asyncio
async def test_fallback_returns_primary_on_success():
    """Test that FallbackProvider uses primary if it succeeds."""
    primary = AsyncMock()
    fallback = AsyncMock()
    
    primary_response = AIResponse(
        content="Success from primary",
        model="gpt-4o",
        provider="openai"
    )
    primary.chat.return_value = primary_response
    
    provider = FallbackProvider(primary=primary, fallback=fallback)
    
    messages = [ChatMessage(role="user", content="Hello")]
    response = await provider.chat(messages)
    
    assert response.content == "Success from primary"
    assert provider._using_fallback is False
    
    primary.chat.assert_called_once()
    fallback.chat.assert_not_called()
