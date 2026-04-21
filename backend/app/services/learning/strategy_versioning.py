"""
Strategy Versioning Service.

Menyimpan snapshot parameter strategi (weights, thresholds) 
dan memungkinkan rollback jika performa menurun.
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.risk_state import RiskState # Reusing check status
from app.services.agent_scorer import AgentScorer
from app.core.logging import get_logger

logger = get_logger(__name__)

class StrategyVersioning:
    """Service untuk versioning dan rollback strategi."""

    def __init__(self, db: Session, scorer: AgentScorer):
        self.db = db
        self.scorer = scorer

    def save_version(self, reason: str = "scheduled_update") -> str:
        """
        Simpan snapshot parameter saat ini ke dalam metadata_json di RiskState.
        (Menyimpan di JSON untuk kemudahan di MVP).
        """
        state = self.db.query(RiskState).first()
        if not state: return "ERROR"

        weights = self.scorer.get_weights()
        version_data = {
            "version_id": f"v_{datetime.utcnow().strftime('%Y%m%d_%H%M')}",
            "weights": weights,
            "timestamp": datetime.utcnow().isoformat(),
            "reason": reason
        }

        # Keep last 10 versions in JSON list
        versions = state.metadata_json.get("strategy_versions", [])
        versions.append(version_data)
        state.metadata_json["strategy_versions"] = versions[-10:] # Cap to 10
        
        # Mark as changed for SQLAlchemy
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(state, "metadata_json")
        
        self.db.commit()
        logger.info("strategy_version_saved", version=version_data["version_id"])
        return version_data["version_id"]

    def rollback(self) -> bool:
        """
        Rollback ke versi sebelumnya.
        """
        state = self.db.query(RiskState).first()
        if not state: return False

        versions = state.metadata_json.get("strategy_versions", [])
        if len(versions) < 2:
            logger.warning("no_previous_version_available")
            return False

        # Get the version before current (last - 2)
        previous = versions[-2]
        
        # Apply weights back to AgentScorer
        # (This requires a new method in AgentScorer to force-override)
        logger.warning("rolling_back_strategy", to_version=previous["version_id"])
        
        # Implement force-apply in scorer
        from app.models.agent_score import AgentScore
        for name, weight in previous["weights"].items():
            agent_score = self.db.query(AgentScore).filter(AgentScore.agent_name == name).first()
            if agent_score:
                agent_score.weight = weight
                
        self.db.commit()
        return True
