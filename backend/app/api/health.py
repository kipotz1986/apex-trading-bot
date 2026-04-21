"""
Deep Health Check API Router.
Verifies connectivity to all critical backend dependencies.
"""

from fastapi import APIRouter, status, Response
from sqlalchemy import text
from app.api import deps
from app.core.database import SessionLocal
from app.core.config import settings
from app.core.logging import get_logger
import redis
import httpx
import time

logger = get_logger(__name__)
router = APIRouter()

@router.get("/health")
async def health_check(response: Response):
    """
    Performs a heart-beat check on all system dependencies.
    Returns 200 if OK, 503 if any critical dependency is down.
    """
    health = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "0.1.0",
        "components": {}
    }
    
    is_healthy = True

    # 1. Database Check
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        health["components"]["database"] = "connected"
        db.close()
    except Exception as e:
        health["components"]["database"] = f"error: {str(e)}"
        is_healthy = False

    # 2. Redis Check
    try:
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.ping()
        health["components"]["redis"] = "connected"
    except Exception as e:
        health["components"]["redis"] = f"error: {str(e)}"
        is_healthy = False

    # 3. ChromaDB Check (Optional/Non-critical for startup)
    try:
        # Simple port check for ChromaDB
        async with httpx.AsyncClient(timeout=2.0) as client:
             # Assuming ChromaDB is at localhost:8000 when running in same network
             # But in Docker it's apex-chromadb:8000
             # We use settings.CHROMADB_HOST
             url = f"http://{settings.CHROMADB_HOST}:{settings.CHROMADB_PORT}/api/v1/heartbeat"
             res = await client.get(url)
             if res.status_code == 200:
                 health["components"]["chromadb"] = "connected"
             else:
                 health["components"]["chromadb"] = f"status_{res.status_code}"
    except Exception:
        health["components"]["chromadb"] = "disconnected"

    if not is_healthy:
        health["status"] = "unhealthy"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return health
