"""
Proportional Sizing Logic for Copy Trading.
"""

from typing import Dict, Any

class CopySizing:
    """Service untuk menghitung ukuran posisi proporsional."""

    @staticmethod
    def calculate(
        trader_balance: float,
        trader_position_size: float,
        user_balance: float,
        safety_factor: float = 0.5
    ) -> float:
        """
        Hitung ukuran posisi berdasarkan proporsi trader asli.
        
        Formula: (trader_pos / trader_bal) * user_bal * safety_factor
        """
        if trader_balance <= 0:
            return 0.0
            
        proportion = trader_position_size / trader_balance
        user_size = proportion * user_balance * safety_factor
        
        return round(user_size, 2)
