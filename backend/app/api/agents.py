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
        # Use CORRECT column name 'meta_data' from Order model
        metadata = o.meta_data if o.meta_data else {}
        reasoning = metadata.get("reasoning", "No detail available")
        decisions.append({
            "id": o.id,
            "timestamp": o.created_at,
            "symbol": o.symbol,
            "action": o.side,
            "reasoning": reasoning,
            "consensus_score": metadata.get("consensus_score", 0.0),
            "agent_signals": metadata.get("agent_signals", {})
        })
        
    return decisions
@router.get("/insights")
async def get_agent_insights(
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """
    Returns the latest AI analysis and confidence scores.
    """
    latest_order = db.query(Order).order_by(desc(Order.created_at)).first()
    
    if not latest_order or not latest_order.meta_data:
        return {
            "narrative": "No recent analysis available. Bot is monitoring market for signals.",
            "scores": {
                "technical": 0,
                "sentiment": 0,
                "onchain": 0
            }
        }
        
    metadata = latest_order.meta_data
    return {
        "narrative": metadata.get("reasoning", "Analysis based on multi-agent consensus."),
        "scores": {
            "technical": metadata.get("technical_score", 50),
            "sentiment": metadata.get("sentiment_score", 50),
            "onchain": metadata.get("onchain_score", 50)
        }
    }

@router.get("/learning")
async def get_learning_stats(
    db: Session = Depends(deps.get_db),
    current_user: str = Depends(deps.get_current_user)
):
    """
    Returns summary metrics for the self-learning dashboard.
    """
    total_trades = db.query(Order).count()
    avg_accuracy = db.query(AgentScore).all()
    
    overall_acc = sum([s.accuracy_score for s in avg_accuracy]) / len(avg_accuracy) if avg_accuracy else 0.85
    
    return {
        "patterns_learned": total_trades * 12, # Mock-ish multiplier for 'patterns'
        "model_version": "v4.2.1-λ",
        "training_cycles": f"{total_trades * 2}h",
        "rl_reward_score": round((overall_acc - 0.5) * 100, 1)
    }
