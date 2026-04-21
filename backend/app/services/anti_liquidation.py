"""
Anti-Liquidation Guard.

Memonitor margin ratio dan rasio likuidasi untuk mencegah 
likuidasi paksa oleh exchange.
"""

from typing import Dict, Any, List
from app.services.execution import ExecutionEngine
from app.core.logging import get_logger

logger = get_logger(__name__)

class AntiLiquidationGuard:
    """Service untuk proteksi margin harian dan likuidasi."""

    # Thresholds
    WARNING_RATIO = 50.0  # % margin used
    DANGER_RATIO = 80.0   # % margin used -> Reduce 50%
    CRITICAL_RATIO = 90.0 # % margin used -> Close all

    def __init__(self, execution_engine: ExecutionEngine):
        self.executor = execution_engine

    async def check_and_protect(self, exchange_positions: List[Dict[str, Any]]):
        """
        Cek setiap posisi dan lakukan proteksi jika risiko likuidasi tinggi.
        """
        for pos in exchange_positions:
            symbol = pos["symbol"]
            # Bybit/Binance often provide 'liquidationPrice' or 'marginRatio'
            liq_price = float(pos.get("liquidationPrice", 0) or 0)
            mark_price = float(pos.get("markPrice", 0) or 0)
            side = pos.get("side", "").upper()
            
            if liq_price == 0 or mark_price == 0:
                continue

            # Hitung jarak ke likuidasi
            distance = abs(mark_price - liq_price) / mark_price if mark_price > 0 else 1.0
            
            if distance < 0.05: # Jarak kurang dari 5% harga saat ini
                logger.warning("CRITICAL_LIQUIDATION_RISK", symbol=symbol, distance=f"{distance:.2%}")
                # Emergency close to save remaining equity
                await self.executor.close_position(symbol, side, float(pos["contracts"]))
                # Notify (could be integrated with Telegram later)
                
            elif distance < 0.10: # Jarak kurang dari 10%
                logger.warning("HIGH_LIQUIDATION_RISK", symbol=symbol, distance=f"{distance:.2%}")
                # Partial reduce (50%)
                await self.executor.close_position(symbol, side, float(pos["contracts"]) * 0.5)
