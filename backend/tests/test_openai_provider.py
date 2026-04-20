import pytest
from unittest.mock import AsyncMock, patch
from app.core.providers.openai_provider import OpenAIProvider
from app.core.ai_provider import ChatMessage

class MockOpenAIResponse:
    def __init__(self, content, model, prompt_tokens, completion_tokens):
        self.choices = [AsyncMock(message=AsyncMock(content=content))]
        self.model = model
        self.usage = AsyncMock(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )

@pytest.mark.asyncio
async def test_openai_chat_returns_ai_response():
    """Test that chat() returns a valid AIResponse."""
    provider = OpenAIProvider(api_key="test-key", model="gpt-4o")
    
    with patch.object(provider.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = MockOpenAIResponse(
            content="BUY signal detected",
            model="gpt-4o",
            prompt_tokens=100,
            completion_tokens=50,
        )
        
        messages = [ChatMessage(role="user", content="Analyze BTC")]
        response = await provider.chat(messages)
        
        assert response.content == "BUY signal detected"
        assert response.provider == "openai"
        assert response.usage["total_tokens"] == 150
        assert response.model == "gpt-4o"

@pytest.mark.asyncio
async def test_openai_analyze_shortcut():
    """Test the analyze() shortcut method."""
    provider = OpenAIProvider(api_key="test-key", model="gpt-4o")
    
    with patch.object(provider.chat, 'return_value', new_callable=AsyncMock) as mock_chat:
        from app.core.ai_provider import AIResponse
        mock_chat.return_value = AIResponse(
            content="Analysis result",
            model="gpt-4o",
            provider="openai",
            usage={"total_tokens": 100}
        )
        
        response = await provider.analyze(
            system_prompt="Analyst",
            data="OHLCV",
            instruction="Predict"
        )
        
        assert response.content == "Analysis result"
        mock_chat.assert_called_once()
