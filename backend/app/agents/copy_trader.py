"""
Copy Trading Agent (Stub).
Akan diimplementasikan penuh pada Epic 6.
Saat ini hanya menyediakan antarmuka mock untuk Master Orchestrator.
"""

from app.schemas.agent_signal import AgentSignal
from app.core.ai_provider import AIProvider

class CopyTradingAgent:
    """Agent stub untuk fitur copy trading."""
    
    AGENT_NAME = "copy_trader"

    def __init__(self, ai_provider: AIProvider = None):
        self.ai = ai_provider

    async def analyze(self, symbol: str) -> AgentSignal:
        """Mock analysis return NEUTRAL."""
        return AgentSignal(
            agent_name=self.AGENT_NAME,
            symbol=symbol,
            signal="NEUTRAL",
            confidence=0.5,
            reasoning="Copy Trading feature is currently disabled (Epic 6 pending)."
        )
