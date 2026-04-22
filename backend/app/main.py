from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.logging import setup_logging, get_logger
from app.core.config import settings
from app.core.limiter import limiter
from app.api import auth, portfolio, trades, bot, websocket, settings as api_settings, agents, health
import signal
import asyncio

# Initialize structured logging
setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="APEX Trading Bot API",
    description="Advanced Multi-Agent AI Trading Bot Backend",
    version="0.1.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.NEXTAUTH_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router, prefix="/api", tags=["System"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["Portfolio"])
app.include_router(trades.router, prefix="/api/trades", tags=["Trade History"])
app.include_router(bot.router, prefix="/api/bot", tags=["Bot Control"])
app.include_router(api_settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(agents.router, prefix="/api/agents", tags=["AI Agents"])
app.include_router(websocket.router, tags=["Websocket"])

@app.on_event("startup")
async def startup_event():
    logger.info("application_startup",
                env=settings.APP_ENV,
                log_level=settings.LOG_LEVEL,
                timezone=settings.TIMEZONE)

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("application_shutdown_initiated")
    # Clean up any resources
    # Positions are intentionally NOT closed here.
    logger.info("application_shutdown_complete")

@app.get("/")
async def root():
    return {"message": "APEX Trading Bot API is running"}
