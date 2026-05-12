"""
Telegram Notification Service.

Mengirim pesan, laporan, dan alert ke owner via Telegram.
Didesain untuk memberikan visibilitas real-time terhadap aktivitas bot.
"""

import httpx
from app.core.config import settings
from app.core.logging import get_logger
from app.core.database import SessionLocal
from app.models.system_settings import SystemSettings

logger = get_logger(__name__)

class TelegramService:
    """Service untuk komunikasi via Telegram."""

    def __init__(self, db=None):
        self._db = db
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        self.client = httpx.AsyncClient(timeout=30)

    def _refresh_config(self):
        """Refresh config from DB if session exists."""
        if self._db:
            db_token = SystemSettings.get_value(self._db, "telegram_bot_token")
            db_chat = SystemSettings.get_value(self._db, "telegram_chat_id")
            if db_token:
                self.token = db_token
            if db_chat:
                self.chat_id = db_chat
            self.api_url = f"https://api.telegram.org/bot{self.token}"
        elif not self.token or not self.chat_id:
            # Try to get a temporary session if not provided
            db = SessionLocal()
            try:
                db_token = SystemSettings.get_value(db, "telegram_bot_token")
                db_chat = SystemSettings.get_value(db, "telegram_chat_id")
                if db_token:
                    self.token = db_token
                if db_chat:
                    self.chat_id = db_chat
                self.api_url = f"https://api.telegram.org/bot{self.token}"
            finally:
                db.close()

    async def send_message(
        self,
        text: str,
        parse_mode: str = "HTML",
        disable_notification: bool = False
    ) -> bool:
        """
        Kirim pesan teks ke owner.
        """
        self._refresh_config()
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

    async def send_decision_alert(
        self,
        symbol: str,
        action: str,
        confidence: float,
        consensus_score: float,
        position_size_usd: float,
        leverage: int,
        regime: str,
        reasoning: str,
        agent_signals: dict,
    ) -> bool:
        """Notifikasi setiap keputusan eksekusi (EXECUTE_LONG / EXECUTE_SHORT)."""
        side_emoji = "📈" if "LONG" in action else "📉" if "SHORT" in action else "⏸️"

        # Compact agent signal line
        sig_lines = []
        for name, sig in (agent_signals or {}).items():
            label = sig.get("signal") if isinstance(sig, dict) else getattr(sig, "signal", "?")
            conf = sig.get("confidence") if isinstance(sig, dict) else getattr(sig, "confidence", 0)
            sig_lines.append(f"  • {name.title()}: <b>{label}</b> ({conf:.0%})")

        body = (
            f"<b>Symbol:</b> {symbol}\n"
            f"<b>Action:</b> {action}\n"
            f"<b>Confidence:</b> {confidence:.0%}  |  <b>Score:</b> {consensus_score:+.2f}\n"
            f"<b>Size:</b> ${position_size_usd:,.2f}  |  <b>Leverage:</b> {leverage}x\n"
            f"<b>Regime:</b> {regime}\n\n"
            f"<b>Agent Signals:</b>\n" + "\n".join(sig_lines) + "\n\n"
            f"<i>{reasoning[:300]}</i>"
        )

        return await self.send_alert(
            level="success",
            title=f"{side_emoji} EXECUTION DECISION",
            body=body,
        )

    async def send_daily_summary(
        self,
        equity: float,
        pnl_today: float,
        pnl_today_pct: float,
        win_rate: float,
        trades_today: int,
        open_positions: int,
        mode: str,
    ) -> bool:
        """Daily morning summary (07:00 WIB)."""
        pnl_emoji = "🟢" if pnl_today >= 0 else "🔴"
        pnl_sign = "+" if pnl_today >= 0 else ""

        body = (
            f"<b>Mode:</b> {mode}\n"
            f"<b>Total Equity:</b> ${equity:,.2f}\n"
            f"<b>PnL Today:</b> {pnl_emoji} {pnl_sign}${pnl_today:,.2f} ({pnl_sign}{pnl_today_pct:.2f}%)\n"
            f"<b>Win Rate:</b> {win_rate:.1f}%\n"
            f"<b>Trades Today:</b> {trades_today}\n"
            f"<b>Open Positions:</b> {open_positions}"
        )

        return await self.send_alert(
            level="info",
            title="☀️ DAILY SUMMARY",
            body=body,
        )

    async def close(self):
        """Clean up resources."""
        await self.client.aclose()
