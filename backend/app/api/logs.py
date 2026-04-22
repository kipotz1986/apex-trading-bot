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
    
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "logs": logs
    }
