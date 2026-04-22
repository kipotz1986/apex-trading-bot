"""
Google Gemini Provider Implementation.

Mengimplementasikan AIProvider interface untuk Google Gemini API.
"""

import google.generativeai as genai
from app.core.ai_provider import AIProvider, AIResponse, ChatMessage
from app.core.logging import get_logger
from app.services.integration_logger import log_integration

logger = get_logger(__name__)


class GoogleProvider(AIProvider):
    """Implementasi AIProvider untuk Google Gemini."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        super().__init__(api_key=api_key, model=model)
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(model)
        logger.info("google_provider_initialized", model=model)

    @log_integration(service_type="AI_PROVIDER", provider_name="GOOGLE", endpoint="chat")
    async def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> AIResponse:
        """Kirim percakapan ke Google Gemini."""
        try:
            # Convert ChatMessage ke format Gemini (role: parts)
            history = []
            for msg in messages[:-1]:
                role = "user" if msg.role == "user" else "model"
                history.append({"role": role, "parts": [msg.content]})
            
            # Start chat session
            chat_session = self.client.start_chat(history=history)
            
            # Setup generation config
            config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                response_mime_type="application/json" if json_mode else "text/plain"
            )
            
            # Send message
            last_msg = messages[-1].content
            response = await chat_session.send_message_async(
                last_msg, 
                generation_config=config
            )
            
            # Usage info
            # Gemini response usually contains usage info in response.usage_metadata
            usage = {
                "prompt_tokens": response.usage_metadata.prompt_token_count,
                "completion_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count,
            }

            logger.info("google_chat_completed",
                model=self.model,
                tokens_used=usage["total_tokens"]
            )

            return AIResponse(
                content=response.text,
                model=self.model,
                provider="google",
                usage=usage,
                raw_response=response,
            )

        except Exception as e:
            logger.error("google_chat_error",
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
        """Shortcut untuk analisis data."""
        messages = [
            ChatMessage(role="user", content=f"SYSTEM PROMPT: {system_prompt}"),
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

    @log_integration(service_type="AI_PROVIDER", provider_name="GOOGLE", endpoint="embed")
    async def embed(self, text: str) -> list[float]:
        """Generate embedding menggunakan Google Generative AI."""
        try:
            result = genai.embed_content(
                model="models/embedding-001",
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            logger.error("google_embed_error", error=str(e))
            raise

    async def health_check(self) -> bool:
        """Cek health status Gemini API."""
        try:
            # Minimal call to check key
            genai.get_model(f"models/{self.model}")
            return True
        except Exception:
            return False
