"""
OpenAI Provider Implementation.

Mengimplementasikan AIProvider interface untuk OpenAI API.
Mendukung model: gpt-4o, gpt-4-turbo, gpt-4.1, gpt-3.5-turbo
"""

from openai import AsyncOpenAI
from app.core.ai_provider import AIProvider, AIResponse, ChatMessage
from app.core.logging import get_logger

logger = get_logger(__name__)


class OpenAIProvider(AIProvider):
    """Implementasi AIProvider untuk OpenAI."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        super().__init__(api_key=api_key, model=model)
        self.client = AsyncOpenAI(api_key=api_key)
        logger.info("openai_provider_initialized", model=model)

    async def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> AIResponse:
        """Kirim chat completion ke OpenAI API."""
        try:
            # Convert ChatMessage ke format OpenAI
            oai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            # Setup request kwargs
            kwargs = {
                "model": self.model,
                "messages": oai_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            # Jika json_mode, tambahkan response_format
            if json_mode:
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
                model=self.model,
                tokens_used=usage["total_tokens"]
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
        )

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

    async def health_check(self) -> bool:
        """Cek apakah OpenAI API sedang online."""
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False
