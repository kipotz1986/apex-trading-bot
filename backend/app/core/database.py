"""
Database configuration.
Setup SQLAlchemy engine, session, and declarative base.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# engine initialization
# check DATABASE_URL from settings
engine = create_engine(
    settings.DATABASE_URL,
    # pool_pre_ping=True helps with long-lived connections
    pool_pre_ping=True
)

# SessionLocal is the class for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all database models
Base = declarative_base()

def get_db():
    """FastAPI dependency to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
