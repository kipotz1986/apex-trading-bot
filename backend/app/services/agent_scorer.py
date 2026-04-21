"""
Agent Scorer Service.

Mengelola skor performa dan perhitungan bobot dinamis untuk
setiap agen menggunakan fungsi Softmax.
"""

import numpy as np
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from app.models.agent_score import AgentScore
from app.core.logging import get_logger

logger = get_logger(__name__)

class AgentScorer:
    """Service untuk manajemen bobot dinamis agen."""

    MIN_WEIGHT = 0.05
    INITIAL_AGENTS = ["technical", "fundamental", "sentiment", "copy_trader"]

    def __init__(self, db: Session):
        self.db = db

    def get_weights(self) -> Dict[str, float]:
        """
        Ambil bobot terbaru dari database. 
        Jika belum ada, inisialisasi default.
        """
        scores = self.db.query(AgentScore).all()
        
        if not scores:
            self._initialize_default_scores()
            scores = self.db.query(AgentScore).all()
            
        return {s.agent_name: s.weight for s in scores}

    def update_performance(self, trade_result: Dict[str, Any]):
        """
        Update skor menggunakan EMA (Exponential Moving Average).
        Recency bias: Performa terbaru lebih berbobot.
        
        trade_result: {
            "pnl_pct": float,
            "agent_signals": { "technical": "BUY", ... },
            "is_neutral_win": bool # Jika market flat dan agent bilang NEUTRAL -> Reward
        }
        """
        pnl = trade_result.get("pnl_pct", 0.0)
        alpha = 0.2  # EMA factor (0.2 means 20% weight to newest trade)
        
        scores = self.db.query(AgentScore).all()
        for s in scores:
            signal_obj = trade_result["agent_signals"].get(s.agent_name)
            if not signal_obj:
                continue
            
            # Mendukung string atau object AgentSignal
            signal = signal_obj.signal if hasattr(signal_obj, "signal") else str(signal_obj)
                
            # 1. Tentukan per-trade score (R)
            # R = +100 (Correct), -100 (Wrong), +10 (Neutral in flat market)
            r = 0.0
            
            if pnl > 0.5: # Winning Trade
                r = 100.0 if "BUY" in signal or "LONG" in signal else -100.0
            elif pnl < -0.5: # Losing Trade
                r = 100.0 if "SELL" in signal or "SHORT" in signal else -100.0
            else: # Flat Market (|pnl| <= 0.5%)
                r = 20.0 if "NEUTRAL" in signal else -10.0

            # 2. Update EMA Score: S_new = (1-alpha)*S_old + alpha*R
            s.score = (1 - alpha) * s.score + alpha * r
            
            # 3. Stats update
            if r > 0: s.successful_trades += 1
            s.total_trades += 1
            
            # Stability floor/ceiling
            s.score = max(min(s.score, 500.0), -500.0)
            
        # Re-calculate weights using Softmax
        self._rebalance_weights()
        self.db.commit()
        logger.info("agent_weights_ema_updated", scores={s.agent_name: round(s.score, 2) for s in scores})

    def _initialize_default_scores(self):
        """Buat entri awal untuk semua agen."""
        for name in self.INITIAL_AGENTS:
            score_entry = AgentScore(
                agent_name=name,
                score=100.0,
                weight=1.0 / len(self.INITIAL_AGENTS)
            )
            self.db.add(score_entry)
        self.db.commit()

    def _rebalance_weights(self):
        """Hitung ulang bobot menggunakan Softmax dari skor."""
        agents = self.db.query(AgentScore).all()
        names = [a.agent_name for a in agents]
        raw_scores = np.array([a.score for a in agents])
        
        # Softmax: exp(s_i) / sum(exp(s_j))
        # Skalakan skor agar softmax tidak meledak atau terlalu rata
        scaled_scores = raw_scores / 100.0 
        exp_scores = np.exp(scaled_scores)
        softmax_weights = exp_scores / np.sum(exp_scores)
        
        # Terapkan floor 0.05
        # 1. Pastikan setiap weight >= MIN_WEIGHT
        # 2. Redistribusi sisanya agar total = 1.0
        n = len(agents)
        min_total = n * self.MIN_WEIGHT
        
        if min_total > 1.0: # Pengaman
             final_weights = [1.0/n] * n
        else:
            # Shift weights so each is >= MIN_WEIGHT
            # Logic: final = MIN_WEIGHT + (softmax * (1.0 - min_total))
            final_weights = self.MIN_WEIGHT + (softmax_weights * (1.0 - min_total))
            
        # Update database
        for a, w in zip(agents, final_weights):
            a.weight = float(round(w, 4))
