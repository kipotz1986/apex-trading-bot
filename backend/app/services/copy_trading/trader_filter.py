"""
Trader Filter Service.

Filtrasi dan skoring algoritma untuk memilih trader terbaik yang stabil.
"""

from typing import List, Dict, Any
from app.schemas.copy_trading import TraderStats
from app.core.logging import get_logger

logger = get_logger(__name__)

class TraderFilter:
    """Service untuk menyeleksi trader berkualitas tinggi."""

    # Kriteria eliminasi minimal
    MIN_WIN_RATE = 65.0
    MIN_DAYS = 30
    MAX_DRAWDOWN = 25.0
    MIN_TRADES = 50

    def filter_and_score(self, traders: List[TraderStats]) -> List[Dict[str, Any]]:
        """
        Filter trader yang tidak memenuhi kriteria,
        lalu hitung composite score untuk ranking.
        """
        qualified = []
        
        for t in traders:
            # 1. Elimination Checklist
            if t.win_rate_pct < self.MIN_WIN_RATE: continue
            if t.track_record_days < self.MIN_DAYS: continue
            if t.max_drawdown_pct > self.MAX_DRAWDOWN: continue
            if t.roi_pct <= 0: continue
            
            # 2. Composite Scoring
            # Score = (ROI * 0.3) + (WinRate * 0.3) + (1 - Drawdown/100)*0.2 + (Days/365 * 0.2)
            # Normalisasi sederhana
            norm_roi = min(1.0, t.roi_pct / 200.0)
            norm_win = t.win_rate_pct / 100.0
            norm_dd = 1.0 - (t.max_drawdown_pct / 100.0)
            norm_days = min(1.0, t.track_record_days / 365.0)
            
            score = (norm_roi * 0.3) + (norm_win * 0.3) + (norm_dd * 0.2) + (norm_days * 0.2)
            
            trader_dict = t.model_dump()
            trader_dict["composite_score"] = round(score, 4)
            qualified.append(trader_dict)

        # Sort by score descending
        qualified.sort(key=lambda x: x["composite_score"], reverse=True)
        
        logger.info("traders_filtered", total=len(traders), qualified=len(qualified))
        return qualified[:10] # Ambil top 10
