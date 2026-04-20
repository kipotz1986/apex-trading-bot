"""
Structured JSON Logging Configuration.

Semua log di aplikasi APEX menggunakan format JSON terstruktur.
Import logger dari sini:
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("trade_executed", pair="BTC/USDT", side="BUY")
"""

import logging
import sys
import structlog
from app.core.config import settings


def setup_logging() -> None:
    """Setup structured logging untuk seluruh aplikasi."""

    # Tentukan log level dari config
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            # Jika development, pakai format berwarna yang mudah dibaca
            # Jika production, pakai format JSON
            structlog.dev.ConsoleRenderer()
            if settings.APP_ENV == "development"
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Dapatkan logger instance untuk module tertentu.
    
    Usage:
        logger = get_logger(__name__)
        logger.info("something_happened", key="value")
        logger.error("something_failed", error=str(e))
    """
    return structlog.get_logger(name)
