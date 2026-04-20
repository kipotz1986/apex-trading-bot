import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.providers.anthropic_provider import AnthropicProvider
from app.core.ai_provider import ChatMessage, AIResponse

class MockAnthropicResponse:
    def __init__(self, content, input_tokens, output_tokens):
        # Claude returns content as a list of text objects
        self.content = [MagicMock(text=content)]
        self.usage = MagicMock(
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )
        self.model = "claude-3-sonnet"

@pytest.mark.asyncio
async def test_anthropic_chat_returns_ai_response():
    """Test that AnthropicProvider.chat() returns a valid AIResponse."""
    # Patch AsyncAnthropic class itself to avoid any real client initialization
    with patch('app.core.providers.anthropic_provider.AsyncAnthropic') as mock_async_client:
        provider = AnthropicProvider(api_key="test-key", model="claude-3-sonnet")
        
        # Mocking the client.messages.create call
        mock_instance = mock_async_client.return_value
        mock_instance.messages = MagicMock()
        mock_instance.messages.create = AsyncMock()
        
        mock_instance.messages.create.return_value = MockAnthropicResponse(
            content="HOLD position",
            input_tokens=150,
            output_tokens=75
        )
        
        messages = [ChatMessage(role="user", content="Analyze SOL")]
        response = await provider.chat(messages)
        
        assert response.content == "HOLD position"
        assert response.provider == "anthropic"
        assert response.usage["total_tokens"] == 225
        assert response.model == "claude-3-sonnet"

@pytest.mark.asyncio
async def test_anthropic_analyze_shortcut():
    """Test the analyze() shortcut method for Anthropic Claude."""
    with patch('app.core.providers.anthropic_provider.AsyncAnthropic'):
        provider = AnthropicProvider(api_key="test-key", model="claude-3-sonnet")
        
        with patch.object(provider, 'chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = AIResponse(
                content="Analysis result",
                model="claude-3-sonnet",
                provider="anthropic",
                usage={"total_tokens": 100}
            )
            
            response = await provider.analyze(
                system_prompt="Analyst",
                data="OHLCV",
                instruction="Predict"
            )
            
            assert response.content == "Analysis result"
            mock_chat.assert_called_once()

@pytest.mark.asyncio
async def test_anthropic_embed_raises_not_implemented():
    """Test that embed() raises NotImplementedError."""
    with patch('app.core.providers.anthropic_provider.AsyncAnthropic'):
        provider = AnthropicProvider(api_key="test-key", model="claude-3-sonnet")
        
        with pytest.raises(NotImplementedError, match="Anthropic does not provide an embedding API yet"):
            await provider.embed("some text")

@pytest.mark.asyncio
async def test_anthropic_health_check_success():
    """Test health_check() returns True when Anthropic API responds."""
    with patch('app.core.providers.anthropic_provider.AsyncAnthropic') as mock_async_client:
        provider = AnthropicProvider(api_key="test-key", model="claude-3-sonnet")
        
        mock_instance = mock_async_client.return_value
        mock_instance.messages = MagicMock()
        mock_instance.messages.create = AsyncMock()
        mock_instance.messages.create.return_value = MagicMock()
        
        result = await provider.health_check()
        assert result is True

@pytest.mark.asyncio
async def test_anthropic_health_check_failure():
    """Test health_check() returns False when Anthropic API fails."""
    with patch('app.core.providers.anthropic_provider.AsyncAnthropic') as mock_async_client:
        provider = AnthropicProvider(api_key="test-key", model="claude-3-sonnet")
        
        mock_instance = mock_async_client.return_value
        mock_instance.messages = MagicMock()
        mock_instance.messages.create = AsyncMock()
        mock_instance.messages.create.side_effect = Exception("API Error")
        
        result = await provider.health_check()
        assert result is False
