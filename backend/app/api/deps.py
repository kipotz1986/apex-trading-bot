"""
Authentication and security dependencies for FastAPI endpoints.
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import BaseModel
from app.core.config import settings
from app.core.database import SessionLocal
from sqlalchemy.orm import Session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

class TokenData(BaseModel):
    username: Optional[str] = None

def get_db() -> Generator:
    """Dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """
    Dependency that validates the JWT token and returns the current user.
    Since this is a single-owner bot, we mainly validate against the admin spec.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        from app.core.security import verify_token
        username = verify_token(token, expected_type="access")
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    if token_data.username != settings.ADMIN_USERNAME:
        raise credentials_exception
        
    return token_data.username
