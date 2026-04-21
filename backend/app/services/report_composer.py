"""
Report Composer Service.

Mengompilasi data performa trading, kesehatan bot, dan insight pasar 
menjadi laporan harian (Daily Report) dalam bahasa Indonesia.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.order import Order
from app.models.risk_state import RiskState
from app.core.logging import get_logger

logger = get_logger(__name__)

class ReportComposer:
    """Service pengolah laporan harian."""

    def __init__(self, db: Session):
        self.db = db

    async def compose_daily_report(self) -> str:
        """
        Membangun teks laporan harian lengkap.
        """
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        
        # 1. Fetch Data
        risk_state = self.db.query(RiskState).first()
        trades_24h = self.db.query(Order).filter(
            Order.closed_at >= yesterday
        ).all()
        
        # 2. Portfolio Stats
        equity = risk_state.current_equity if risk_state else 0.0
        peak = risk_state.equity_peak if risk_state else 0.0
        drawdown = ((peak - equity) / peak * 100) if peak > 0 else 0.0
        
        # 3. Trade Performance
        total_trades = len(trades_24h)
        wins = [t for t in trades_24h if t.pnl_usd > 0]
        net_pnl = sum(t.pnl_usd for t in trades_24h)
        win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0.0
        
        best_trade = max(trades_24h, key=lambda x: x.pnl_usd) if trades_24h else None
        
        # 4. Compose Message
        report = [
            f"📊 <b>APEX Daily Report — {now.strftime('%d %B %Y')}</b>",
            "",
            "💰 <b>Portfolio</b>",
            f"• Keuntungan Bersih: {'+' if net_pnl >= 0 else ''}${net_pnl:.2f}",
            f"• Ekuitas Saat Ini: ${equity:,.2f}",
            f"• Max Drawdown: {drawdown:.1f}%",
            "",
            "📈 <b>Kinerja 24 Jam</b>",
            f"• Total Trade: {total_trades}",
            f"• Win / Loss: {len(wins)} / {total_trades - len(wins)} ({win_rate:.1f}%)",
        ]
        
        if best_trade:
            report.append(f"• Best Trade: {best_trade.symbol} {'LONG' if best_trade.side == 'BUY' else 'SHORT'} (+${best_trade.pnl_usd:.2f})")
            
        report.extend([
            "",
            "🤖 <b>AI Insights & Health</b>",
            f"• Status: {'✅ Running' if not risk_state or risk_state.system_status == 'NORMAL' else '⚠️ ' + risk_state.system_status}",
            f"• Mode: {'Live' if risk_state and risk_state.is_live_enabled else 'Paper Trading'}",
            f"• Consecutive Losses: {risk_state.consecutive_losses if risk_state else 0}",
            "",
            "<i>Pasar kripto bersifat volatil. Tetaplah disiplin pada manajemen risiko.</i>"
        ])
        
        return "\n".join(report)
