"""
Anthropic Claude Provider Implementation.

Mengimplementasikan AIProvider interface untuk Anthropic Claude API.
"""

from anthropic import AsyncAnthropic
from app.core.ai_provider import AIProvider, AIResponse, ChatMessage
from app.core.logging import get_logger

logger = get_logger(__name__)


class AnthropicProvider(AIProvider):
    """Implementasi AIProvider untuk Anthropic Claude."""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20240620"):
        super().__init__(api_key=api_key, model=model)
        self.client = AsyncAnthropic(api_key=api_key)
        logger.info("anthropic_provider_initialized", model=model)

    async def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> AIResponse:
        """Kirim percakapan ke Anthropic Claude."""
        try:
            # Claude mengirim system prompt sebagai parameter terpisah
            system_msg = ""
            anthropic_messages = []
            
            for msg in messages:
                if msg.role == "system":
                    system_msg = msg.content
                else:
                    anthropic_messages.append({"role": msg.role, "content": msg.content})

            # Setup kwargs
            kwargs = {
                "model": self.model,
                "messages": anthropic_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if system_msg:
                kwargs["system"] = system_msg

            # Claude tidak punya native JSON mode lewat API parameter
            # Kita tangani lewat prompting jika json_mode=True
            if json_mode:
                if system_msg:
                    kwargs["system"] += "\nIMPORTANT: Your response must be valid JSON."
                else:
                    kwargs["system"] = "IMPORTANT: Your response must be valid JSON."

            response = await self.client.messages.create(**kwargs)
            
            usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            }

            logger.info("anthropic_chat_completed",
                model=self.model,
                tokens_used=usage["total_tokens"]
            )

            return AIResponse(
                content=response.content[0].text,
                model=self.model,
                provider="anthropic",
                usage=usage,
                raw_response=response,
            )

        except Exception as e:
            logger.error("anthropic_chat_error",
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
        """Shortcut untuk analisis data menggunakan Claude."""
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(
                role="user",
                content=f"## DATA:\n{data}\n\n## INSTRUCTION:\n{instruction}"
            ),
        ]
        return await self.chat(
            messages=messages,
            temperature=0.3,
            json_mode=json_mode,
        )

    async def embed(self, text: str) -> list[float]:
        """
        Claude tidak menyediakan API embedding publik.
        Mengembalikan error yang informatif.
        """
        logger.warning("anthropic_embedding_not_supported")
        raise NotImplementedError("Anthropic does not provide an embedding API yet. Use OpenAI for embeddings.")

    async def health_check(self) -> bool:
        """Cek health status Anthropic API."""
        try:
            # Minimal call to check key
            await self.client.messages.create(
                model=self.model,
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}]
            )
            return True
        except Exception:
            return False
