"""
Telegram Notification Service.

Mengirim pesan, laporan, dan alert ke owner via Telegram.
Didesain untuk memberikan visibilitas real-time terhadap aktivitas bot.
"""

import httpx
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class TelegramService:
    """Service untuk komunikasi via Telegram."""

    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        self.client = httpx.AsyncClient(timeout=30)

    async def send_message(
        self,
        text: str,
        parse_mode: str = "HTML",
        disable_notification: bool = False
    ) -> bool:
        """
        Kirim pesan teks ke owner.
        """
        if not self.token or not self.chat_id:
            logger.warning("telegram_config_missing")
            return False

        try:
            response = await self.client.post(
                f"{self.api_url}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_notification": disable_notification,
                },
            )
            data = response.json()
            
            if data.get("ok"):
                logger.debug("telegram_message_sent")
                return True
            else:
                logger.error("telegram_send_failed", error=data)
                return False

        except Exception as e:
            logger.error("telegram_error", error=str(e))
            return False

    async def send_alert(self, level: str, title: str, body: str) -> bool:
        """
        Kirim alert dengan emoji sesuai level.
        level: "critical" | "warning" | "info" | "success"
        """
        emojis = {
            "critical": "🔴",
            "warning": "🟡",
            "info": "🔵",
            "success": "🟢",
        }
        
        emoji = emojis.get(level.lower(), "ℹ️")
        message = f"{emoji} <b>{title}</b>\n\n{body}"
        
        return await self.send_message(message)

    async def close(self):
        """Clean up resources."""
        await self.client.aclose()
