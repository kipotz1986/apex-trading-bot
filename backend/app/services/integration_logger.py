import time
import asyncio
import functools
import traceback
from datetime import datetime
from typing import Any, Callable, Dict, Optional
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.integration_log import IntegrationLog
from app.core.logging import get_logger
from app.api.websocket import broadcast_updates

logger = get_logger(__name__)

class IntegrationLogger:
    """
    Utility for logging 3rd-party API requests and broadcasting to WebSocket.
    """

    @staticmethod
    async def log_request(
        service_type: str,
        provider_name: str,
        endpoint: str,
        status: str,
        latency_ms: int,
        error_details: Optional[str] = None
    ):
        """
        Persists log to database and broadcasts to WebSocket.
        """
        db = SessionLocal()
        try:
            new_log = IntegrationLog(
                service_type=service_type,
                provider_name=provider_name,
                endpoint=endpoint,
                status=status,
                latency_ms=latency_ms,
                error_details=error_details
            )
            db.add(new_log)
            db.commit()
            db.refresh(new_log)

            # Broadcast to WebSocket
            log_data = {
                "id": new_log.id,
                "timestamp": new_log.timestamp.isoformat(),
                "service_type": new_log.service_type,
                "provider_name": new_log.provider_name,
                "endpoint": new_log.endpoint,
                "status": new_log.status,
                "latency_ms": new_log.latency_ms,
                "error_details": new_log.error_details
            }
            
            # Fire and forget WS broadcast
            asyncio.create_task(broadcast_updates("system_logs", log_data))

        except Exception as e:
            logger.error("integration_logging_failed", error=str(e))
        finally:
            db.close()

def log_integration(service_type: str, provider_name: str, endpoint: str):
    """
    Decorator to automatically log 3rd-party integration calls.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "SUCCESS"
            error_details = None
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "ERROR"
                error_details = f"{str(e)}\n{traceback.format_exc()}"
                raise e
            finally:
                latency_ms = int((time.time() - start_time) * 1000)
                # Run logging in background to not block main execution
                asyncio.create_task(
                    IntegrationLogger.log_request(
                        service_type=service_type,
                        provider_name=provider_name,
                        endpoint=endpoint,
                        status=status,
                        latency_ms=latency_ms,
                        error_details=error_details
                    )
                )
        return wrapper
    return decorator
