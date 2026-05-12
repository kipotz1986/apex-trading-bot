"""
Reward Function Service.

Menghitung 'hadiah' atau 'hukuman' bagi RL agent berdasarkan 
kualitas keputusan trading yang diambil.
"""

from typing import Dict, Any

class RewardFunction:
    """Service untuk kalkulasi reward RL."""

    def calculate(self, trade_result: Dict[str, Any]) -> float:
        """
        Input: {
            "pnl_pct": float,
            "max_drawdown_during_trade": float,
            "had_sl": bool,
            "is_overtrading": bool,
            "hold_time_minutes": int
        }
        """
        reward = 0.0
        
        # 1. PnL Component (Bobot Utama)
        pnl_pct = trade_result.get("pnl_pct", 0.0)
        reward += pnl_pct * 1.0 # 1% profit = +1.0 reward
        
        # 2. Risk Adjusted Penalty
        # Jika drawdown saat trade > 2%, berikan penalty meski akhirnya profit
        mdd = trade_result.get("max_drawdown_during_trade", 0.0)
        if mdd > 2.0:
            reward -= (mdd - 2.0) * 0.5
            
        # 3. Discipline Bonuses
        if trade_result.get("had_sl", False):
            reward += 0.2 # Bonus karena disiplin pasang SL
            
        # 4. Efficiency Component (Sharpe-like)
        # Menghargai profit yang didapat dengan risiko/volatilitas rendah
        if pnl_pct > 0 and mdd > 0:
            efficiency = pnl_pct / mdd
            reward += min(efficiency * 0.1, 0.5)

        # 5. Leverage Penalty
        # Jika menggunakan leverage terlalu tinggi (> 5x)
        leverage = trade_result.get("leverage", 1.0)
        if leverage > 5:
            reward -= (leverage - 5) * 0.1

        # 6. Overtrading Penalty
        if trade_result.get("hold_time_minutes", 0) < 5:
            reward -= 0.5
            
        # Cap reward to prevent outliers
        return max(min(reward, 10.0), -10.0)
