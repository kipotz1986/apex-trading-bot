"""
Daily Refresh Leaderboard Script.
Mendapatkan data trader terbaik dan memperbarui database.
"""

import asyncio
from app.core.database import SessionLocal
from app.services.copy_trading.leaderboard import BybitLeaderboardService
from app.services.copy_trading.trader_filter import TraderFilter
from app.models.copy_trade import TopTrader
from app.core.logging import get_logger

logger = get_logger(__name__)

async def refresh_leaderboard():
    """Alur refresh leaderboard."""
    db = SessionLocal()
    try:
        logger.info("starting_leaderboard_refresh")
        
        # 1. Fetch
        service = BybitLeaderboardService()
        raw_traders = await service.fetch()
        
        # 2. Filter & Score
        filtrator = TraderFilter()
        top_10 = filtrator.filter_and_score(raw_traders)
        
        # 3. Update DB
        # Deactivate all current top traders first
        db.query(TopTrader).update({TopTrader.is_active: False})
        
        for t_data in top_10:
            trader = db.query(TopTrader).filter(TopTrader.trader_id == t_data["trader_id"]).first()
            if not trader:
                trader = TopTrader(trader_id=t_data["trader_id"])
                db.add(trader)
            
            # Update stats
            trader.username = t_data["username"]
            trader.roi_pct = t_data["roi_pct"]
            trader.win_rate_pct = t_data["win_rate_pct"]
            trader.pnl_usd = t_data["pnl_usd"]
            trader.max_drawdown_pct = t_data["max_drawdown_pct"]
            trader.track_record_days = t_data["track_record_days"]
            trader.followers_count = t_data["followers_count"]
            trader.composite_score = t_data["composite_score"]
            trader.is_active = True
            
        db.commit()
        logger.info("leaderboard_refresh_completed", new_count=len(top_10))
        
    except Exception as e:
        logger.error("leaderboard_refresh_failed", error=str(e))
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(refresh_leaderboard())
