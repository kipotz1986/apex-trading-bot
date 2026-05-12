from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.logging import setup_logging, get_logger
from app.core.config import settings
from app.core.limiter import limiter
from app.api import auth, portfolio, trades, bot, websocket, settings as api_settings, agents, health, backtest, logs

# Initialize structured logging
setup_logging()
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from app.db.init_timescale import init_timescale_db
    from app.services.bot_runner import bot_runner
    from app.services.market_stream import market_stream
    
    # Run DB init
    init_timescale_db()
    
    # Enforce Encryption Key and validate it is a proper Fernet key
    if not settings.ENCRYPTION_KEY:
        logger.error("startup_failed_missing_encryption_key")
        raise RuntimeError("ENCRYPTION_KEY is required to start the application.")
    try:
        from app.core.encryption import encrypt
        encrypt("startup-validation-check")
    except Exception as fernet_err:
        raise RuntimeError(f"ENCRYPTION_KEY is set but invalid (must be 32-byte URL-safe base64): {fernet_err}")

    # Start background services
    await bot_runner.start()
    await market_stream.start()
    
    logger.info("application_startup_complete",
                env=settings.APP_ENV,
                log_level=settings.LOG_LEVEL,
                timezone=settings.TIMEZONE)
    yield
    # Shutdown
    logger.info("application_shutdown_complete")

app = FastAPI(
    title="APEX Trading Bot API",
    description="Advanced Multi-Agent AI Trading Bot Backend",
    version="0.1.0",
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration
_cors_origins = [settings.NEXTAUTH_URL]
if settings.APP_ENV == "development":
    _cors_origins.append("http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# Routes
app.include_router(health.router, prefix="/api", tags=["System"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["Portfolio"])
app.include_router(trades.router, prefix="/api/trades", tags=["Trade History"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["Backtesting"])
app.include_router(logs.router, prefix="/api/logs", tags=["Logs"])
app.include_router(bot.router, prefix="/api/bot", tags=["Bot Control"])
app.include_router(api_settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(agents.router, prefix="/api/agents", tags=["AI Agents"])
app.include_router(websocket.router, tags=["Websocket"])

@app.on_event("shutdown")
async def shutdown_event():
    from app.services.bot_runner import bot_runner
    from app.services.market_stream import market_stream
    logger.info("application_shutdown_initiated")
    # Stop the trading loop
    await bot_runner.stop()
    # Stop market data streaming
    await market_stream.stop()
    # Clean up any resources
    # Positions are intentionally NOT closed here.
    logger.info("application_shutdown_complete")

@app.get("/")
async def root():
    return {"message": "APEX Trading Bot API is running"}
