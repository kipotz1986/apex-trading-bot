"""
Application configuration.
Membaca environment variables dari file .env dan menyediakan
typed settings yang bisa diakses di seluruh aplikasi.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Semua konfigurasi aplikasi. Nilai dibaca dari .env file.
    Jika variabel tidak ada di .env, gunakan default yang tertera.
    """

    # === AI Provider ===
    AI_PROVIDER: str = "openai"
    AI_MODEL: str = "gpt-4o"
    AI_API_KEY: str = ""
    AI_FALLBACK_PROVIDER: Optional[str] = None
    AI_FALLBACK_MODEL: Optional[str] = None
    AI_FALLBACK_API_KEY: Optional[str] = None

    # === Exchange ===
    EXCHANGE_NAME: str = "bybit"
    EXCHANGE_API_KEY: str = ""
    EXCHANGE_API_SECRET: str = ""
    EXCHANGE_TESTNET: bool = True  # True = paper trading (aman)

    # === On-Chain Data ===
    WHALE_ALERT_API_KEY: str = ""
    GLASSNODE_API_KEY: str = ""
    CRYPTOQUANT_API_KEY: str = ""

    # === Database ===
    DATABASE_URL: str = "postgresql://apex:apex_dev_password@localhost:5432/apex_trading"
    REDIS_URL: str = "redis://localhost:6379/0"
    CHROMADB_HOST: str = "localhost"
    CHROMADB_PORT: int = 8000

    # === Telegram ===
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # === Auth ===
    JWT_SECRET: str = ""
    NEXTAUTH_SECRET: str = ""
    NEXTAUTH_URL: str = "http://localhost:3000"

    # === App ===
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    TIMEZONE: str = "Asia/Jakarta"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Singleton instance — import ini di mana saja:
# from app.core.config import settings
settings = Settings()
