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

from contextvars import ContextVar

logger = get_logger(__name__)

# Context variable to store metadata for the current request
# This allows services to "attach" real URL/Method info during execution
request_metadata: ContextVar[Dict[str, Any]] = ContextVar("request_metadata", default={})

class IntegrationLogger:
    """
    Utility for logging 3rd-party API requests and broadcasting to WebSocket.
    """

    @staticmethod
    def record_request(url: str, method: str = "GET", headers: Optional[Dict] = None, body: Any = None):
        """Helper to record actual external request details inside a function."""
        request_metadata.set({
            "url": url,
            "method": method,
            "headers": headers,
            "request_body": body
        })

    @staticmethod
    def get_metadata() -> Dict[str, Any]:
        return request_metadata.get()

    @staticmethod
    async def log_request(
        service_type: str,
        provider_name: str,
        endpoint: str,
        status: str,
        latency_ms: int,
        error_details: Optional[str] = None,
        prompt_data: Optional[Dict] = None,
        external_api_data: Optional[Dict] = None
    ):
        """
        Persists log to database and broadcasts to WebSocket.
        """
        db = SessionLocal()
        try:
            # Clear context after use
            request_metadata.set({})
            
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

            # Insert PromptLog if available
            if prompt_data and service_type == "AI_PROVIDER":
                from app.models.prompt_log import PromptLog
                prompt_log = PromptLog(
                    integration_log_id=new_log.id,
                    timestamp=new_log.timestamp,
                    prompt_input=prompt_data.get("input"),
                    prompt_output=prompt_data.get("output"),
                    model_name=prompt_data.get("model"),
                    agent_name=prompt_data.get("agent_name"),
                    prompt_tokens=prompt_data.get("prompt_tokens", 0),
                    completion_tokens=prompt_data.get("completion_tokens", 0),
                    total_tokens=prompt_data.get("total_tokens", 0)
                )
                db.add(prompt_log)
                db.commit()
            
            # Insert ExternalApiLog if available
            if external_api_data and service_type != "AI_PROVIDER":
                from app.models.external_api_log import ExternalApiLog
                api_log = ExternalApiLog(
                    integration_log_id=new_log.id,
                    timestamp=new_log.timestamp,
                    url=external_api_data.get("url"),
                    method=external_api_data.get("method"),
                    request_body=external_api_data.get("request_body"),
                    response_body=external_api_data.get("response_body"),
                    headers=external_api_data.get("headers")
                )
                db.add(api_log)
                db.commit()

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
            
            if prompt_data:
                log_data["prompt_details"] = {
                    "prompt_input": prompt_data.get("input"),
                    "prompt_output": prompt_data.get("output"),
                    "model_name": prompt_data.get("model"),
                    "agent_name": prompt_data.get("agent_name"),
                    "prompt_tokens": prompt_data.get("prompt_tokens", 0),
                    "completion_tokens": prompt_data.get("completion_tokens", 0),
                    "total_tokens": prompt_data.get("total_tokens", 0)
                }
            
            if external_api_data:
                log_data["external_api_details"] = external_api_data
            
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
            # Reset context for this call
            request_metadata.set({})
            
            start_time = time.time()
            status = "SUCCESS"
            error_details = None
            prompt_data = None
            external_api_data = None
            
            try:
                result = await func(*args, **kwargs)
                
                # Check if it's an AIProvider call
                if service_type == "AI_PROVIDER" and hasattr(result, "content") and hasattr(result, "usage"):
                    prompt_input = None
                    messages = kwargs.get("messages")
                    if not messages and len(args) > 1:
                        messages = args[1]
                        
                    if isinstance(messages, list) and len(messages) > 0:
                        prompt_input = "\n\n".join([f"{getattr(m, 'role', 'user').upper()}: {getattr(m, 'content', str(m))}" for m in messages])
                    elif isinstance(messages, str):
                        prompt_input = messages
                    
                    prompt_data = {
                        "input": prompt_input,
                        "output": result.content,
                        "model": getattr(result, "model", None),
                        "prompt_tokens": result.usage.get("prompt_tokens", 0) if result.usage else 0,
                        "completion_tokens": result.usage.get("completion_tokens", 0) if result.usage else 0,
                        "total_tokens": result.usage.get("total_tokens", 0) if result.usage else 0,
                        "agent_name": kwargs.get("agent_name")
                    }
                
                # For non-AI calls, capture request/response as external_api_data
                elif service_type != "AI_PROVIDER":
                    import json
                    try:
                        # 1. Check if metadata was manually recorded inside the function
                        meta = request_metadata.get()
                        
                        # 2. Fallback to generic serialization if no meta
                        if not meta.get("url"):
                            # Serialize args/kwargs as request body
                            # Skip 'self' in args
                            req_args = args[1:] if args else []
                            req_body = {
                                "args": req_args,
                                "kwargs": kwargs
                            }
                            url = getattr(args[0], "url", None) if args else None
                            method = "INTERNAL_CALL"
                        else:
                            url = meta.get("url")
                            method = meta.get("method", "GET")
                            req_body = meta.get("request_body") or {"args": args[1:], "kwargs": kwargs}

                        # Serialize result as response body
                        res_body = result
                        
                        external_api_data = {
                            "url": url,
                            "method": method,
                            "request_body": json.dumps(req_body, default=str),
                            "response_body": json.dumps(res_body, default=str),
                            "headers": json.dumps(meta.get("headers"), default=str) if meta.get("headers") else None
                        }
                    except Exception:
                        pass
                    
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
                        error_details=error_details,
                        prompt_data=prompt_data,
                        external_api_data=external_api_data
                    )
                )
        return wrapper
    return decorator
