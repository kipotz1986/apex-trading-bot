from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from app.api import deps
from app.models.integration_log import IntegrationLog
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("/integration")
async def get_integration_logs(
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    service_type: Optional[str] = None,
    status: Optional[str] = None
):
    """
    Returns a paginated list of integration logs.
    """
    query = db.query(IntegrationLog)
    
    if service_type:
        query = query.filter(IntegrationLog.service_type == service_type.upper())
    if status:
        query = query.filter(IntegrationLog.status == status.upper())
        
    total = query.count()
    logs = query.order_by(desc(IntegrationLog.timestamp)).offset((page - 1) * per_page).limit(per_page).all()
    
    # Fetch prompt details for AI_PROVIDER logs
    ai_provider_log_ids = [log.id for log in logs if log.service_type == "AI_PROVIDER"]
    other_log_ids = [log.id for log in logs if log.service_type != "AI_PROVIDER"]
    
    details_map = {}
    
    if ai_provider_log_ids:
        from app.models.prompt_log import PromptLog
        prompts = db.query(PromptLog).filter(PromptLog.integration_log_id.in_(ai_provider_log_ids)).all()
        for p in prompts:
            details_map[p.integration_log_id] = {
                "type": "prompt",
                "data": {
                    "prompt_input": p.prompt_input,
                    "prompt_output": p.prompt_output,
                    "model_name": p.model_name,
                    "agent_name": p.agent_name,
                    "prompt_tokens": p.prompt_tokens,
                    "completion_tokens": p.completion_tokens,
                    "total_tokens": p.total_tokens
                }
            }
            
    if other_log_ids:
        from app.models.external_api_log import ExternalApiLog
        api_logs = db.query(ExternalApiLog).filter(ExternalApiLog.integration_log_id.in_(other_log_ids)).all()
        for a in api_logs:
            details_map[a.integration_log_id] = {
                "type": "external_api",
                "data": {
                    "url": a.url,
                    "method": a.method,
                    "request_body": a.request_body,
                    "response_body": a.response_body,
                    "headers": a.headers
                }
            }
            
    # Serialize logs
    serialized_logs = []
    for log in logs:
        log_dict = {
            "id": log.id,
            "timestamp": log.timestamp.isoformat() if hasattr(log.timestamp, "isoformat") else log.timestamp,
            "service_type": log.service_type,
            "provider_name": log.provider_name,
            "endpoint": log.endpoint,
            "status": log.status,
            "latency_ms": log.latency_ms,
            "error_details": log.error_details
        }
        
        if log.id in details_map:
            detail = details_map[log.id]
            if detail["type"] == "prompt":
                log_dict["prompt_details"] = detail["data"]
            else:
                log_dict["external_api_details"] = detail["data"]
                
        serialized_logs.append(log_dict)
    
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "logs": serialized_logs
    }
