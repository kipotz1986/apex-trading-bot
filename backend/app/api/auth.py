"""
API Authentication Router.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
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

class Verify2FARequest(BaseModel):
    totp_code: str

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
    
    # Check password hash (if set, otherwise allow 'admin' for initial setup)
    if settings.ADMIN_PASSWORD_HASH:
        if not security.verify_password(form_data.password, settings.ADMIN_PASSWORD_HASH):
            log_audit(db, "login_failed", form_data.username, {"reason": "wrong_password"}, ip_address=request.client.host)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )
    else:
        # Emergency fallback for initial setup only
        if form_data.password != "admin":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )

    # If we made it here, credentials are correct.
    log_audit(db, "login_step_1_success", form_data.username, ip_address=request.client.host)
    
    # Return a temporary token for 2FA verification.
    temp_token = security.create_temp_token(data={"sub": form_data.username, "type": "temp"})
    
    return {
        "requires_2fa": True,
        "temp_token": temp_token
    }

@router.post("/verify-2fa", response_model=TokenResponse)
async def verify_2fa(
    request: Verify2FARequest,
    # Need to manually validate temp token from header if needed, but for simplicity:
    current_user: str = Depends(deps.get_current_user) 
):
    """
    Step 2: Verify TOTP code and return the final Access Token.
    """
    # Logic for TOTP verification
    if settings.TOTP_SECRET:
        if not security.verify_totp(settings.TOTP_SECRET, request.totp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code",
            )
    else:
        # If no secret configured (initial setup), we might want to skip or allow a specific code
        # For security, we should ideally force a secret setup.
        pass

    access_token = security.create_access_token(data={"sub": current_user})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def get_me(current_user: str = Depends(deps.get_current_user)):
    """Returns current user info."""
    return {"username": current_user, "role": "owner"}
