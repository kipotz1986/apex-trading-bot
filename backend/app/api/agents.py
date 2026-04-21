"""
Agents and Decision Logs API Router.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from app.api import deps
from app.models.agent_score import AgentScore
from app.models.order import Order
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("/scores")
async def get_agent_scores(
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """Returns current accuracy scores for all AI agents."""
    scores = db.query(AgentScore).all()
    return scores

@router.get("/decisions")
async def get_decision_log(
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user),
    limit: int = 20
):
    """
    Returns recent decisions made by the orchestrator.
    This data is extracted from the orders metadata.
    """
    orders = db.query(Order).order_by(desc(Order.created_at)).limit(limit).all()
    
    decisions = []
    for o in orders:
        reasoning = o.metadata_json.get("reasoning", "No detail available")
        decisions.append({
            "id": o.id,
            "timestamp": o.created_at,
            "symbol": o.symbol,
            "action": o.side,
            "reasoning": reasoning,
            "consensus_score": o.metadata_json.get("consensus_score", 0.0),
            "agent_signals": o.metadata_json.get("agent_signals", {})
        })
        
    return decisions
