import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.providers.google_provider import GoogleProvider
from app.core.ai_provider import ChatMessage, AIResponse

class MockUsageMetadata:
    def __init__(self, p_tokens, c_tokens):
        self.prompt_token_count = p_tokens
        self.candidates_token_count = c_tokens
        self.total_token_count = p_tokens + c_tokens

class MockGoogleResponse:
    def __init__(self, text, p_tokens, c_tokens):
        self.text = text
        self.usage_metadata = MockUsageMetadata(p_tokens, c_tokens)

@pytest.mark.asyncio
async def test_google_chat_returns_ai_response():
    """Test that GoogleProvider.chat() returns a valid AIResponse."""
    # Patch genai.configure and genai.GenerativeModel
    with patch('google.generativeai.configure'), \
         patch('google.generativeai.GenerativeModel') as mock_model:
        
        provider = GoogleProvider(api_key="test-key", model="gemini-1.5-pro")
        
        # Mock the async call to send_message_async via a mock chat session
        mock_chat_session = AsyncMock()
        mock_model.return_value.start_chat.return_value = mock_chat_session
        
        mock_chat_session.send_message_async.return_value = MockGoogleResponse(
            text="SELL signal detected",
            p_tokens=120,
            c_tokens=60
        )
        
        messages = [ChatMessage(role="user", content="Analyze ETH")]
        response = await provider.chat(messages)
        
        assert response.content == "SELL signal detected"
        assert response.provider == "google"
        assert response.usage["total_tokens"] == 180
        assert response.model == "gemini-1.5-pro"

@pytest.mark.asyncio
async def test_google_analyze_shortcut():
    """Test the analyze() shortcut method for Google Gemini."""
    with patch('google.generativeai.configure'), \
         patch('google.generativeai.GenerativeModel'):
        
        provider = GoogleProvider(api_key="test-key", model="gemini-1.5-pro")
        
        with patch.object(provider, 'chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = AIResponse(
                content="Analysis result",
                model="gemini-1.5-pro",
                provider="google",
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
async def test_google_embed_success():
    """Test the embed() method using Google Gemini."""
    with patch('google.generativeai.configure'), \
         patch('google.generativeai.GenerativeModel'), \
         patch('google.generativeai.embed_content') as mock_embed:
        
        provider = GoogleProvider(api_key="test-key", model="gemini-1.5-pro")
        mock_embed.return_value = {'embedding': [0.1, 0.2, 0.3]}
        
        result = await provider.embed("test text")
        assert result == [0.1, 0.2, 0.3]

@pytest.mark.asyncio
async def test_google_health_check_success():
    """Test health_check() returns True when Google API is accessible."""
    with patch('google.generativeai.configure'), \
         patch('google.generativeai.GenerativeModel'), \
         patch('google.generativeai.get_model') as mock_get_model:
        
        provider = GoogleProvider(api_key="test-key", model="gemini-1.5-pro")
        mock_get_model.return_value = MagicMock()
        
        result = await provider.health_check()
        assert result is True

@pytest.mark.asyncio
async def test_google_health_check_failure():
    """Test health_check() returns False when Google API fails."""
    with patch('google.generativeai.configure'), \
         patch('google.generativeai.GenerativeModel'), \
         patch('google.generativeai.get_model') as mock_get_model:
        
        provider = GoogleProvider(api_key="test-key", model="gemini-1.5-pro")
        mock_get_model.side_effect = Exception("API Error")
        
        result = await provider.health_check()
        assert result is False
