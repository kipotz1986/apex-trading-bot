"""
AI Provider Abstraction Layer.

Semua AI provider (OpenAI, Gemini, Claude, dll) HARUS
mengimplementasikan interface ini. Ini memastikan kita bisa
swap provider tanpa mengubah kode agent apapun.

Usage:
    from app.core.ai_provider import get_ai_provider
    provider = get_ai_provider()
    response = await provider.chat(messages=[...])
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import BaseModel
from app.core.config import settings


class ChatMessage(BaseModel):
    """Representasi satu pesan dalam percakapan."""
    role: str  # "system", "user", "assistant"
    content: str


class AIResponse(BaseModel):
    """Respons standar dari AI provider manapun."""
    content: str          # Teks respons utama
    model: str            # Model yang digunakan (e.g., "gpt-4o")
    provider: str         # Provider (e.g., "openai")
    usage: dict = {}      # Token usage {"prompt_tokens": x, "completion_tokens": y}
    raw_response: Any = None  # Raw response asli dari provider (untuk debugging)


class AIProvider(ABC):
    """
    Abstract base class untuk semua AI Provider.
    
    Setiap provider baru (OpenAI, Gemini, Claude, dll) HARUS:
    1. Inherit dari class ini
    2. Implementasi semua method yang ada @abstractmethod
    3. Dibuat di file terpisah (e.g., openai_provider.py)
    """

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> AIResponse:
        """
        Kirim percakapan ke AI dan dapatkan respons.
        """
        pass

    @abstractmethod
    async def analyze(
        self,
        system_prompt: str,
        data: str,
        instruction: str,
        json_mode: bool = True,
    ) -> AIResponse:
        """
        Shortcut untuk analisis data. Mengirim system prompt + data + instruksi.
        """
        pass

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """
        Convert teks menjadi vektor embedding.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Cek apakah provider ini sedang online dan API key valid.
        """
        pass


def _create_provider(name: str, model: str, api_key: str) -> AIProvider:
    """Helper internal untuk instansiasi provider."""
    if name == "openai":
        from app.core.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=api_key, model=model)
    elif name == "google":
        from app.core.providers.google_provider import GoogleProvider
        return GoogleProvider(api_key=api_key, model=model)
    elif name == "anthropic":
        from app.core.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(api_key=api_key, model=model)
    else:
        raise ValueError(f"Unknown AI provider: '{name}'")


def get_ai_provider(
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> AIProvider:
    """
    Factory function — dapatkan AI provider sesuai konfigurasi.
    Implementasi Fallback otomatis jika dikonfigurasi di .env.
    """
    from app.core.providers.fallback_provider import FallbackProvider

    name = provider_name or settings.AI_PROVIDER
    mdl = model or settings.AI_MODEL
    key = api_key or settings.AI_API_KEY

    primary = _create_provider(name, mdl, key)

    # Cek apakah ada fallback
    fallback = None
    if not provider_name and settings.AI_FALLBACK_PROVIDER:
         fallback = _create_provider(
             settings.AI_FALLBACK_PROVIDER,
             settings.AI_FALLBACK_MODEL or settings.AI_MODEL,
             settings.AI_FALLBACK_API_KEY or ""
         )

    if fallback:
        return FallbackProvider(primary=primary, fallback=fallback)
    
    return primary
