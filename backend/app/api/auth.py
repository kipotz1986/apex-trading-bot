"""
API Authentication Router.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core import security
from app.core.config import settings
from app.core.limiter import limiter
from app.services.audit_log import log_audit
from app.api import deps
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

class LoginResponse(BaseModel):
    requires_2fa: bool
    temp_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(deps.get_db)):
    """
    Step 1: Validate credentials and return a temporary token for 2FA.
    """
    logger.info("login_attempt", username=form_data.username)
    if form_data.username != settings.ADMIN_USERNAME:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    if not settings.ADMIN_PASSWORD_HASH:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication not configured — ADMIN_PASSWORD_HASH is not set",
        )
    if not security.verify_password(form_data.password, settings.ADMIN_PASSWORD_HASH):
        log_audit(db, "login_failed", form_data.username, {"reason": "wrong_password"}, ip_address=request.client.host)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # If we made it here, credentials are correct.
    log_audit(db, "login_step_1_success", form_data.username, ip_address=request.client.host)
    
    # Return a temporary token for 2FA verification.
    temp_token = security.create_temp_token(subject=form_data.username)
    
    return {
        "requires_2fa": True,
        "temp_token": temp_token
    }

class Verify2FARequest(BaseModel):
    totp_code: str
    temp_token: str

@router.post("/verify-2fa", response_model=TokenResponse)
@limiter.limit("5/minute")
async def verify_2fa(
    request: Request,
    response: Response,
    body: Verify2FARequest,
    db: Session = Depends(deps.get_db)
):
    """
    Step 2: Verify TOTP code and return the final Access Token.
    """
    # Verify temp token
    try:
        username = security.verify_token(body.temp_token, expected_type="temp_2fa")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired temporary token",
        )

    # Logic for TOTP verification
    import pyotp
    if settings.TOTP_SECRET:
        totp = pyotp.TOTP(settings.TOTP_SECRET)
        if not totp.verify(body.totp_code, valid_window=1):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code",
            )

    access_token = security.create_access_token(subject=username)
    log_audit(db, "login_success", username, ip_address=request.client.host)
    # Set httpOnly cookie so the token is never accessible to JavaScript
    is_secure = settings.APP_ENV != "development"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=is_secure,
        samesite="strict",
        max_age=86400,  # 24 hours
        path="/",
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def get_me(current_user: str = Depends(deps.get_current_user)):
    """Returns current user info."""
    return {"username": current_user, "role": "owner"}
