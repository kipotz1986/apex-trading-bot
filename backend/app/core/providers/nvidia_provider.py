"""
NVIDIA NIM Provider Implementation.

Mengimplementasikan AIProvider interface untuk NVIDIA NIM API.
Menggunakan library OpenAI dengan custom base_url.
"""

from openai import AsyncOpenAI
from typing import Optional
from app.core.ai_provider import AIProvider, AIResponse, ChatMessage
from app.core.logging import get_logger
from app.services.integration_logger import log_integration

logger = get_logger(__name__)


class NvidiaProvider(AIProvider):
    """Implementasi AIProvider untuk NVIDIA NIM."""

    def __init__(self, api_key: str, model: str = "meta/llama-3.1-70b-instruct"):
        super().__init__(api_key=api_key, model=model)
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://integrate.api.nvidia.com/v1"
        )
        logger.info("nvidia_provider_initialized", model=model)

    @log_integration(service_type="AI_PROVIDER", provider_name="NVIDIA", endpoint="chat")
    async def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
        agent_name: Optional[str] = None,
        advanced: bool = False,
    ) -> AIResponse:
        """Kirim chat completion ke NVIDIA NIM API."""
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
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

            # NVIDIA API mostly supports JSON mode if the model is llama-3.1 etc., 
            # but response_format might need to be verified. 
            # We will use it if requested.
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            # Panggil API
            response = await self.client.chat.completions.create(**kwargs)

            # Parse response
            choice = response.choices[0]
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            }

            logger.info("nvidia_chat_completed",
                model=target_model,
                tokens_used=usage["total_tokens"],
                advanced=advanced
            )

            return AIResponse(
                content=choice.message.content or "",
                model=response.model,
                provider="nvidia",
                usage=usage,
                raw_response=response,
            )

        except Exception as e:
            logger.error("nvidia_chat_error",
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

    @log_integration(service_type="AI_PROVIDER", provider_name="NVIDIA", endpoint="embed")
    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector. Nvidia has embed API, using a default one."""
        try:
            response = await self.client.embeddings.create(
                model="nvidia/nv-embedqa-e5-v5",
                input=text,
                input_type="query"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error("nvidia_embed_error", error=str(e))
            raise

    async def list_models(self) -> list[str]:
        """Dapatkan daftar model dari NVIDIA NIM."""
        try:
            response = await self.client.models.list()
            # Return model IDs. NIM returns many models.
            models = [m.id for m in response.data]
            return sorted(models)
        except Exception:
            # Fallback
            return [
                "meta/llama-3.1-70b-instruct",
                "meta/llama-3.1-8b-instruct",
                "meta/llama-3.1-405b-instruct",
                "mistralai/mistral-large-2-instruct",
                "nvidia/nemotron-4-340b-instruct"
            ]

    async def health_check(self) -> bool:
        """Cek apakah NVIDIA API sedang online."""
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False
