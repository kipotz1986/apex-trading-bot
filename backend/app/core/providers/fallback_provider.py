"""
Fallback AI Provider.

Wrapper yang mencoba provider utama dulu, jika gagal
otomatis switch ke provider cadangan.
"""

from app.core.ai_provider import AIProvider, AIResponse, ChatMessage
from app.core.logging import get_logger
from typing import Optional

logger = get_logger(__name__)


class FallbackProvider(AIProvider):
    """Provider yang memiliki cadangan otomatis."""

    def __init__(self, primary: AIProvider, fallback: Optional[AIProvider] = None):
        # Gunakan atribut primary untuk model/key info
        super().__init__(api_key=primary.api_key, model=primary.model)
        self.primary = primary
        self.fallback = fallback
        self._using_fallback = False

    async def chat(self, messages: list[ChatMessage], temperature: float = 0.7, max_tokens: int = 4096, json_mode: bool = False) -> AIResponse:
        try:
            response = await self.primary.chat(messages, temperature, max_tokens, json_mode)
            self._using_fallback = False
            return response
        except Exception as primary_error:
            if self.fallback:
                logger.warning("primary_provider_failed_switching_to_fallback",
                    primary=self.primary.__class__.__name__,
                    fallback=self.fallback.__class__.__name__,
                    error=str(primary_error)
                )
                self._using_fallback = True
                return await self.fallback.chat(messages, temperature, max_tokens, json_mode)
            
            logger.error("primary_provider_failed_no_fallback",
                primary=self.primary.__class__.__name__,
                error=str(primary_error)
            )
            raise

    async def analyze(self, system_prompt: str, data: str, instruction: str, json_mode: bool = True) -> AIResponse:
        try:
            response = await self.primary.analyze(system_prompt, data, instruction, json_mode)
            self._using_fallback = False
            return response
        except Exception as primary_error:
            if self.fallback:
                logger.warning("primary_analyze_failed_switching_to_fallback",
                    primary=self.primary.__class__.__name__,
                    fallback=self.fallback.__class__.__name__,
                    error=str(primary_error)
                )
                self._using_fallback = True
                return await self.fallback.analyze(system_prompt, data, instruction, json_mode)
            raise

    async def embed(self, text: str) -> list[float]:
        try:
            return await self.primary.embed(text)
        except Exception as primary_error:
            if self.fallback:
                logger.warning("primary_embed_failed_switching_to_fallback",
                    primary=self.primary.__class__.__name__,
                    fallback=self.fallback.__class__.__name__,
                    error=str(primary_error)
                )
                return await self.fallback.embed(text)
            raise

    async def health_check(self) -> bool:
        """Kesehatan dianggap OK jika primary OK, ATAU fallback OK."""
        primary_ok = await self.primary.health_check()
        if primary_ok:
            return True
        
        if self.fallback:
            return await self.fallback.health_check()
        
        return False
