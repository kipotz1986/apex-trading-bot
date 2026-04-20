import pytest
from unittest.mock import patch, MagicMock
from app.core.ai_provider import get_ai_provider
from app.core.providers.openai_provider import OpenAIProvider
from app.core.providers.google_provider import GoogleProvider
from app.core.providers.fallback_provider import FallbackProvider

@pytest.fixture
def mock_settings():
    with patch('app.core.ai_provider.settings') as mock:
        mock.AI_PROVIDER = "openai"
        mock.AI_MODEL = "gpt-4o"
        mock.AI_API_KEY = "test-key"
        mock.AI_FALLBACK_PROVIDER = None
        yield mock

def test_get_ai_provider_returns_openai(mock_settings):
    """Test factory returns OpenAIProvider by default."""
    provider = get_ai_provider()
    assert isinstance(provider, OpenAIProvider)
    assert provider.model == "gpt-4o"

def test_get_ai_provider_returns_google(mock_settings):
    """Test factory returns GoogleProvider when specified."""
    mock_settings.AI_PROVIDER = "google"
    provider = get_ai_provider()
    assert isinstance(provider, GoogleProvider)

def test_get_ai_provider_with_fallback(mock_settings):
    """Test factory returns FallbackProvider when fallback is configured."""
    mock_settings.AI_FALLBACK_PROVIDER = "google"
    mock_settings.AI_FALLBACK_MODEL = "gemini-pro"
    mock_settings.AI_FALLBACK_API_KEY = "fallback-key"
    
    provider = get_ai_provider()
    assert isinstance(provider, FallbackProvider)
    assert isinstance(provider.primary, OpenAIProvider)
    assert isinstance(provider.fallback, GoogleProvider)

def test_get_ai_provider_invalid_name(mock_settings):
    """Test factory raises ValueError on invalid provider name."""
    with pytest.raises(ValueError, match="Unknown AI provider"):
        get_ai_provider(provider_name="unknown")
