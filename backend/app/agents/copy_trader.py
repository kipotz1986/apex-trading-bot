"""
Copy Trading Agent (Stub).
Akan diimplementasikan penuh pada Epic 6.
Saat ini hanya menyediakan antarmuka mock untuk Master Orchestrator.
"""

from sqlalchemy.orm import Session
from app.models.copy_trade import TopTrader, CopyTradeEvent
from app.schemas.agent_signal import AgentSignal
from app.core.ai_provider import AIProvider

class CopyTradingAgent:
    """Agent stub untuk fitur copy trading."""
    
    AGENT_NAME = "copy_trader"

    def __init__(self, db: Session, ai_provider: AIProvider = None):
        self.db = db
        self.ai = ai_provider

    async def analyze(self, symbol: str) -> AgentSignal:
        """
        Agregasi sinyal dari Top Traders.
        Logic: Jika >= 3 traders open di side yang sama, hasilkan sinyal.
        """
        # 1. Ambil event OPEN terbaru untuk symbol ini (misal dalam 24 jam terakhir)
        all_traders = self.db.query(TopTrader.trader_id).filter(TopTrader.is_active == True).all()
        active_trader_ids = [t.trader_id for t in all_traders]
        
        events = self.db.query(CopyTradeEvent).filter(
            CopyTradeEvent.symbol == symbol,
            CopyTradeEvent.event_type == "OPEN",
            CopyTradeEvent.trader_id.in_(active_trader_ids)
        ).all()
        
        # 2. Count sides
        buy_count = len([e for e in events if e.side == "BUY"])
        sell_count = len([e for e in events if e.side == "SELL"])
        
        signal = "NEUTRAL"
        confidence = 0.0
        reasoning = "Tidak ada konsensus yang cukup dari Top Traders."
        
        # Threshold: Min 3 traders
        if buy_count >= 3:
            signal = "BUY"
            confidence = min(0.9, buy_count / 10.0 + 0.2)
            reasoning = f"{buy_count} dari top traders membuka posisi LONG."
        elif sell_count >= 3:
            signal = "SELL"
            confidence = min(0.9, sell_count / 10.0 + 0.2)
            reasoning = f"{sell_count} dari top traders membuka posisi SHORT."
            
        return AgentSignal(
            agent_name=self.AGENT_NAME,
            symbol=symbol,
            signal=signal,
            confidence=confidence,
            reasoning=reasoning,
            metadata={"traders_count": buy_count if signal == "BUY" else sell_count}
        )
