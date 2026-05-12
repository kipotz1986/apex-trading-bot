"""
System Settings API Router.
"""

from fastapi import APIRouter, Depends, HTTPException, Body, Request
from sqlalchemy.orm import Session
from typing import Dict, Any
from urllib.parse import urlparse
from app.api import deps
from app.core.config import settings
from app.services.audit_log import log_audit
from app.core.logging import get_logger

_ALLOWED_EXCHANGE_HOSTS = {
    "api.bybit.com", "api-testnet.bybit.com", "api-demo.bybit.com",
    "api.binance.com", "testnet.binance.vision",
    "www.okx.com", "aws.okx.com",
}

from app.models.system_settings import SystemSettings
from app.models.audit_log import AuditLog
from app.models.exchange_credential import ExchangeCredential
from app.core.encryption import encrypt, decrypt
from app.services.exchange import ExchangeService
from sqlalchemy import desc

logger = get_logger(__name__)
router = APIRouter()

@router.get("/audit-logs")
async def get_audit_logs(
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user),
    limit: int = 50
):
    """Returns the most recent audit logs."""
    logs = db.query(AuditLog).order_by(desc(AuditLog.timestamp)).limit(limit).all()
    return logs

@router.get("/")
async def get_all_settings(
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """
    Returns application settings. 
    Sensitive keys like API keys are masked.
    """
    # Very Aggressive defaults — bias toward execution
    daily_loss = SystemSettings.get_value(db, "daily_loss_limit", "12.0")
    max_leverage = SystemSettings.get_value(db, "max_leverage", "15")
    max_pos = SystemSettings.get_value(db, "max_position_size", "20.0")
    adv_reasoning = SystemSettings.get_value(db, "advanced_reasoning_enabled", "false").lower() == "true"
    threshold_strong = SystemSettings.get_value(db, "consensus_threshold_strong", "0.4")
    threshold_moderate = SystemSettings.get_value(db, "consensus_threshold_moderate", "0.15")
    ai_provider = SystemSettings.get_value(db, "ai_provider", settings.AI_PROVIDER)
    ai_model = SystemSettings.get_value(db, "ai_model", settings.AI_MODEL)

    # Provider Keys — stored encrypted, never return plaintext
    openai_key_enc = SystemSettings.get_value(db, "ai_api_key_openai", "")
    google_key_enc = SystemSettings.get_value(db, "ai_api_key_google", "")
    anthropic_key_enc = SystemSettings.get_value(db, "ai_api_key_anthropic", "")

    max_total_exposure = SystemSettings.get_value(db, "max_total_exposure", "80.0")
    
    telegram_token = SystemSettings.get_value(db, "telegram_bot_token", settings.TELEGRAM_BOT_TOKEN)
    telegram_chat = SystemSettings.get_value(db, "telegram_chat_id", settings.TELEGRAM_CHAT_ID)

    return {
        "dailyLossLimit": float(daily_loss),
        "maxLeverage": int(max_leverage),
        "maxPositionSize": float(max_pos),
        "maxTotalExposure": float(max_total_exposure),
        "consensusThresholdStrong": float(threshold_strong),
        "consensusThresholdModerate": float(threshold_moderate),
        "aiProvider": ai_provider,
        "advancedReasoningEnabled": adv_reasoning,
        "tradingSymbols": settings.get_symbol_list(),
        "ai": {
            "provider": ai_provider,
            "model": ai_model,
            "openai_api_key": "****" if openai_key_enc else "",
            "google_api_key": "****" if google_key_enc else "",
            "anthropic_api_key": "****" if anthropic_key_enc else "",
        },
        "exchange": {
            "name": settings.EXCHANGE_NAME,
            "api_key": "****" if settings.EXCHANGE_API_KEY else "",
            "testnet": settings.EXCHANGE_TESTNET
        },
        "app": {
            "env": settings.APP_ENV,
            "timezone": settings.TIMEZONE
        },
        "notifications": {
            "telegram_bot_token": "****" if telegram_token else "",
            "telegram_chat_id": telegram_chat
        }
    }

@router.put("/ai")
async def update_ai_settings(
    request: Request,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """Updates AI provider settings."""
    if "advancedReasoningEnabled" in payload:
        SystemSettings.set_value(db, "advanced_reasoning_enabled", str(payload["advancedReasoningEnabled"]).lower())
    if "provider" in payload:
        SystemSettings.set_value(db, "ai_provider", str(payload["provider"]))
    if "model" in payload:
        SystemSettings.set_value(db, "ai_model", str(payload["model"]))
    
    # Save provider keys encrypted; skip if masked (unchanged)
    if payload.get("openai_api_key") and not str(payload["openai_api_key"]).startswith("****"):
        SystemSettings.set_value(db, "ai_api_key_openai", encrypt(payload["openai_api_key"]))
    if payload.get("google_api_key") and not str(payload["google_api_key"]).startswith("****"):
        SystemSettings.set_value(db, "ai_api_key_google", encrypt(payload["google_api_key"]))
    if payload.get("anthropic_api_key") and not str(payload["anthropic_api_key"]).startswith("****"):
        SystemSettings.set_value(db, "ai_api_key_anthropic", encrypt(payload["anthropic_api_key"]))

    # Scrub sensitive fields before audit log
    safe_payload = {k: ("***REDACTED***" if "api_key" in k.lower() or "secret" in k.lower() else v) for k, v in payload.items()}
    log_audit(db, "settings_update_ai", current_user, safe_payload, ip_address=request.client.host)
    logger.info("settings_updated_ai", user=current_user, provider=payload.get("provider"))
    return {"status": "success", "message": "AI settings updated"}

@router.get("/ai/models/{provider}")
async def get_ai_models(
    provider: str,
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """Returns a list of available models for a given provider."""
    from app.core.ai_provider import get_ai_provider
    try:
        # Get provider instance with current key from env/settings
        p = get_ai_provider(provider_name=provider)
        models = await p.list_models()
        return models
    except Exception as e:
        logger.error("failed_to_list_models", provider=provider, error=str(e))
        # Static fallbacks if everything fails
        fallbacks = {
            "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
            "google": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"],
            "anthropic": ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229", "claude-3-haiku-20240307"]
        }
        return fallbacks.get(provider, [])

@router.put("/risk")
async def update_risk_settings(
    request: Request,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """Updates risk management parameters."""
    if "dailyLossLimit" in payload:
        SystemSettings.set_value(db, "daily_loss_limit", str(payload["dailyLossLimit"]))
    if "maxLeverage" in payload:
        SystemSettings.set_value(db, "max_leverage", str(payload["maxLeverage"]))
    if "maxPositionSize" in payload:
        SystemSettings.set_value(db, "max_position_size", str(payload["maxPositionSize"]))
    if "consensusThresholdStrong" in payload:
        SystemSettings.set_value(db, "consensus_threshold_strong", str(payload["consensusThresholdStrong"]))
    if "consensusThresholdModerate" in payload:
        SystemSettings.set_value(db, "consensus_threshold_moderate", str(payload["consensusThresholdModerate"]))
    if "maxTotalExposure" in payload:
        SystemSettings.set_value(db, "max_total_exposure", str(payload["maxTotalExposure"]))

    log_audit(db, "settings_update_risk", current_user, payload, ip_address=request.client.host)
    logger.info("settings_updated_risk", user=current_user)
    return {"status": "success", "message": "Risk parameters updated"}

# Catalog of symbols the bot fully supports (each has dedicated on-chain pipeline)
_SUPPORTED_SYMBOLS = [
    {"symbol": "BTC/USDT:USDT", "name": "Bitcoin", "ticker": "BTC", "onchain_source": "Blockchain.com (hash rate, mempool)"},
    {"symbol": "ETH/USDT:USDT", "name": "Ethereum", "ticker": "ETH", "onchain_source": "Etherscan (gas price, whale transfers)"},
    {"symbol": "SOL/USDT:USDT", "name": "Solana", "ticker": "SOL", "onchain_source": "Solana RPC (TPS, epoch)"},
]


@router.get("/trading-symbols")
async def get_trading_symbols(
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user),
):
    """Returns the active trading symbol list + the catalog of supported symbols."""
    active = settings.get_symbol_list()
    return {
        "active": active,
        "supported": _SUPPORTED_SYMBOLS,
    }


@router.put("/trading-symbols")
async def update_trading_symbols(
    request: Request,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user),
):
    """Update the list of trading symbols the bot will iterate over.
    Body: { "symbols": ["BTC/USDT:USDT", "ETH/USDT:USDT"] }"""
    symbols = payload.get("symbols", [])
    if not isinstance(symbols, list) or not symbols:
        raise HTTPException(status_code=400, detail="At least one symbol required")

    valid_symbols = {s["symbol"] for s in _SUPPORTED_SYMBOLS}
    invalid = [s for s in symbols if s not in valid_symbols]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported symbols: {', '.join(invalid)}. Supported: {', '.join(valid_symbols)}"
        )

    SystemSettings.set_value(db, "trading_symbols", ",".join(symbols))
    log_audit(db, "settings_trading_symbols_changed", current_user,
              {"symbols": symbols}, ip_address=request.client.host)
    logger.info("trading_symbols_updated", user=current_user, count=len(symbols))
    return {"active": symbols, "status": "success"}


@router.get("/mode-profiles")
async def list_mode_profiles(
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user),
):
    """Returns all available bot mode profiles (Conservative → YOLO)."""
    from app.services.mode_profile import list_profiles, get_active_profile
    active = get_active_profile(db)
    return {
        "active_slug": active["slug"],
        "profiles": list_profiles(),
    }


@router.get("/mode-profiles/active")
async def get_active_mode_profile(
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user),
):
    """Returns the currently active mode profile with full parameter details."""
    from app.services.mode_profile import get_active_profile
    return get_active_profile(db)


@router.post("/mode-profiles/{slug}")
async def set_mode_profile(
    slug: str,
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user),
):
    """Apply a named mode profile — writes all its parameters to SystemSettings."""
    from app.services.mode_profile import apply_profile
    try:
        profile = apply_profile(db, slug)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    log_audit(db, "settings_mode_profile_changed", current_user,
              {"slug": slug, "name": profile["name"]},
              ip_address=request.client.host)
    return profile


@router.put("/notifications")
async def update_notification_settings(
    request: Request,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """Updates notification settings (Telegram)."""
    if "telegram_bot_token" in payload and not str(payload["telegram_bot_token"]).startswith("****"):
        SystemSettings.set_value(db, "telegram_bot_token", str(payload["telegram_bot_token"]))
    if "telegram_chat_id" in payload:
        SystemSettings.set_value(db, "telegram_chat_id", str(payload["telegram_chat_id"]))

    log_audit(db, "settings_update_notifications", current_user,
              {k: ("***REDACTED***" if "token" in k.lower() else v) for k, v in payload.items()},
              ip_address=request.client.host)
    logger.info("settings_updated_notifications", user=current_user)
    return {"status": "success", "message": "Notification settings updated"}


@router.post("/notifications/test")
async def test_telegram_notification(
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user),
):
    """Send a test Telegram message to verify token + chat_id are correct."""
    from app.services.telegram import TelegramService
    telegram = TelegramService(db=db)
    try:
        ok = await telegram.send_alert(
            level="success",
            title="✅ APEX TEST MESSAGE",
            body=(
                "Telegram notifications are working correctly.\n\n"
                "You will receive:\n"
                "• Real-time alerts on every execution decision\n"
                "• Daily summary every morning at 07:00 WIB"
            ),
        )
        if not ok:
            raise HTTPException(status_code=400, detail="Telegram send failed. Check bot token and chat ID.")
        return {"status": "success", "message": "Test message sent"}
    finally:
        await telegram.close()

def _is_placeholder_cred(key: str, secret: str) -> bool:
    """True only when key/secret are obviously empty or generic placeholders."""
    return not key or key.startswith("your_") or not secret or secret.startswith("your_")

@router.get("/exchange/profiles")
async def get_exchange_profiles(
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """Returns configured exchange profiles with masked API keys."""
    profiles = db.query(ExchangeCredential).all()
    result = {}
    for p in profiles:
        decrypted_key = decrypt(p.api_key) if p.api_key else ""
        decrypted_secret = decrypt(p.api_secret) if p.api_secret else ""
        masked_key = f"****{decrypted_key[-4:]}" if len(decrypted_key) > 4 else ""
        result[p.profile] = {
            "exchange": p.exchange,
            "api_key": masked_key,
            "base_url": p.base_url,
            "is_active": p.is_active,
            "is_placeholder": _is_placeholder_cred(decrypted_key, decrypted_secret),
        }
    return result

@router.put("/exchange/profiles/{profile}")
async def update_exchange_profile(
    profile: str,
    request: Request,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """Creates or updates an exchange profile. Keys are encrypted before saving."""
    if profile not in ["demo", "live"]:
        raise HTTPException(status_code=400, detail="Profile must be 'demo' or 'live'")

    cred = db.query(ExchangeCredential).filter_by(profile=profile).first()
    if not cred:
        cred = ExchangeCredential(profile=profile)
        db.add(cred)

    logger.info("exchange_profile_update_payload",
        profile=profile,
        payload_keys=list(payload.keys()),
        has_api_key="api_key" in payload,
        api_key_len=len(str(payload.get("api_key") or "")),
        has_api_secret="api_secret" in payload,
        api_secret_len=len(str(payload.get("api_secret") or "")),
    )

    # Only update if provided in payload (allows partial updates or keeping old secret if not sent)
    if "api_key" in payload and payload["api_key"] and not payload["api_key"].startswith("****"):
        cred.api_key = encrypt(payload["api_key"])
        logger.info("exchange_profile_api_key_updated", profile=profile)
    if "api_secret" in payload and payload["api_secret"] and not payload["api_secret"].startswith("****"):
        cred.api_secret = encrypt(payload["api_secret"])
        logger.info("exchange_profile_api_secret_updated", profile=profile)
    if "base_url" in payload:
        cred.base_url = payload["base_url"]

    db.commit()
    log_audit(db, "settings_update_exchange_profile", current_user, {"profile": profile}, ip_address=request.client.host)
    logger.info("exchange_profile_updated", user=current_user, profile=profile)
    return {"status": "success", "message": f"Profile {profile} updated"}

@router.post("/exchange/test-connection")
async def test_exchange_connection(
    request: Request,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """Tests an exchange connection using provided credentials or existing profile."""
    profile = payload.get("profile", "demo")
    api_key = payload.get("api_key")
    api_secret = payload.get("api_secret")
    base_url = payload.get("base_url")

    # If key is masked (or secret missing), fetch real credentials from DB
    if (api_key and api_key.startswith("****")) or not api_secret:
        cred = db.query(ExchangeCredential).filter_by(profile=profile).first()
        if cred and cred.api_key:
            if not api_key or api_key.startswith("****"):
                api_key = decrypt(cred.api_key)
            if not api_secret or api_secret.startswith("****"):
                api_secret = decrypt(cred.api_secret)

    if not api_key or not api_secret:
        raise HTTPException(status_code=400, detail="Valid API key and secret required for testing.")

    try:
        if base_url:
            parsed = urlparse(base_url)
            if parsed.hostname not in _ALLOWED_EXCHANGE_HOSTS:
                raise HTTPException(status_code=400, detail=f"base_url hostname '{parsed.hostname}' is not permitted")

        # Create a temporary exchange instance using configured exchange name
        test_exchange = ExchangeService(
            exchange_name=settings.EXCHANGE_NAME,
            api_key=api_key,
            api_secret=api_secret,
            testnet=(profile == "demo")
        )
        if base_url:
            test_exchange.exchange.urls['api'] = base_url

        # Test connection by fetching balance
        await test_exchange.get_balance()
        await test_exchange.close()
        
        logger.info("exchange_connection_tested", profile=profile, status="success")
        return {"status": "success", "message": "Connection successful"}
    except Exception as e:
        logger.error("exchange_connection_test_failed", profile=profile, error=str(e))
        # Ensure we close it even on failure
        if 'test_exchange' in locals():
            await test_exchange.close()
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")
