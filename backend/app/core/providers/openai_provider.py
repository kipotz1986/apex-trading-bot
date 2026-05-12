"""
OpenAI Provider Implementation.

Mengimplementasikan AIProvider interface untuk OpenAI API.
Mendukung model: gpt-4o, gpt-4-turbo, gpt-4.1, gpt-3.5-turbo
"""

from openai import AsyncOpenAI
from typing import Optional
from app.core.ai_provider import AIProvider, AIResponse, ChatMessage
from app.core.logging import get_logger
from app.services.integration_logger import log_integration

logger = get_logger(__name__)


class OpenAIProvider(AIProvider):
    """Implementasi AIProvider untuk OpenAI."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        super().__init__(api_key=api_key, model=model)
        self.client = AsyncOpenAI(api_key=api_key)
        logger.info("openai_provider_initialized", model=model)

    @log_integration(service_type="AI_PROVIDER", provider_name="OPENAI", endpoint="chat")
    async def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
        agent_name: Optional[str] = None,
        advanced: bool = False,
    ) -> AIResponse:
        """Kirim chat completion ke OpenAI API."""
        try:
            target_model = self.get_advanced_model() if advanced else self.model
            
            # Convert ChatMessage ke format OpenAI
            oai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            # Setup request kwargs
            kwargs = {
                "model": target_model,
                "messages": oai_messages,
            }

            # o1-series models (and potentially newer ones) use max_completion_tokens
            is_new_reasoning_model = any(m in target_model for m in ["o1-", "o3-", "gpt-5"])
            
            if is_new_reasoning_model:
                kwargs["max_completion_tokens"] = max_tokens
            else:
                kwargs["max_tokens"] = max_tokens
                kwargs["temperature"] = temperature

            # Jika json_mode, tambahkan response_format (not supported by o1-preview yet)
            if json_mode and not is_new_reasoning_model:
                kwargs["response_format"] = {"type": "json_object"}

            # Panggil API
            response = await self.client.chat.completions.create(**kwargs)

            # Parse response
            choice = response.choices[0]
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

            logger.info("openai_chat_completed",
                model=target_model,
                tokens_used=usage["total_tokens"],
                advanced=advanced
            )

            return AIResponse(
                content=choice.message.content or "",
                model=response.model,
                provider="openai",
                usage=usage,
                raw_response=response,
            )

        except Exception as e:
            logger.error("openai_chat_error",
                model=self.model,
                error=str(e)
            )
            raise

    async def analyze(
        self,
        system_prompt: str,
        data: str,
        instruction: str,
        json_mode: bool = True,
        agent_name: Optional[str] = None,
        advanced: bool = False,
    ) -> AIResponse:
        """Shortcut untuk analisis — gabungkan system + data + instruction."""
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(
                role="user",
                content=f"## DATA:\n{data}\n\n## INSTRUCTION:\n{instruction}"
            ),
        ]
        return await self.chat(
            messages=messages,
            temperature=0.3,  # Lebih deterministik untuk analisis
            json_mode=json_mode,
            agent_name=agent_name,
            advanced=advanced,
        )

    @log_integration(service_type="AI_PROVIDER", provider_name="OPENAI", endpoint="embed")
    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector menggunakan OpenAI."""
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error("openai_embed_error", error=str(e))
            raise

    async def list_models(self) -> list[str]:
        """Dapatkan daftar model dari OpenAI."""
        try:
            response = await self.client.models.list()
            # Filter hanya model GPT yang relevan untuk trading/chat
            models = [m.id for m in response.data if "gpt" in m.id or "o1-" in m.id or "o3-" in m.id]
            return sorted(models)
        except Exception:
            # Fallback jika API key tidak valid atau error
            return ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]

    async def health_check(self) -> bool:
        """Cek apakah OpenAI API sedang online."""
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False
