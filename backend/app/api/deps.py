"""
Authentication and security dependencies for FastAPI endpoints.
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import BaseModel
from app.core.config import settings
from app.core.database import SessionLocal
from sqlalchemy.orm import Session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

class TokenData(BaseModel):
    username: Optional[str] = None

def get_db() -> Generator:
    """Dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(
    request: Request,
    bearer_token: Optional[str] = Depends(oauth2_scheme),
    cookie_token: Optional[str] = Cookie(default=None, alias="access_token"),
) -> str:
    """
    Validates JWT from httpOnly cookie (preferred) or Authorization header (fallback).
    """
    token = cookie_token or bearer_token
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        from app.core.security import verify_token
        username = verify_token(token, expected_type="access")
        token_data = TokenData(username=username)
    except (JWTError, Exception):
        raise credentials_exception

    if token_data.username != settings.ADMIN_USERNAME:
        raise credentials_exception

    return token_data.username
