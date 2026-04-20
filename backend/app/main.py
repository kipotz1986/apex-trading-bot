"""
APEX Trading Bot — Backend Entrypoint
"""

from fastapi import FastAPI
from app.core.logging import setup_logging, get_logger
from app.core.config import settings

# Initialize structured logging
setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="APEX Trading Bot API",
    description="Advanced Multi-Agent AI Trading Bot Backend",
    version="0.1.0"
)

@app.on_event("startup")
async def startup_event():
    logger.info("application_startup",
                env=settings.APP_ENV,
                log_level=settings.LOG_LEVEL,
                timezone=settings.TIMEZONE)

@app.get("/")
async def root():
    return {"message": "APEX Trading Bot API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
