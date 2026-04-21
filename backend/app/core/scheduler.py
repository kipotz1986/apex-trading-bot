"""
System Scheduler.

Mengelola tugas terjadwal seperti Laporan Harian Telegram 
dan pembersihan data berkala.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.telegram import TelegramService
from app.services.report_composer import ReportComposer
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)

async def send_daily_report_job():
    """Tugas terjadwal untuk mengirim laporan harian."""
    logger.info("scheduled_daily_report_job_triggered")
    db = SessionLocal()
    telegram = TelegramService()
    composer = ReportComposer(db)
    
    try:
        report_text = await composer.compose_daily_report()
        await telegram.send_message(report_text)
        logger.info("scheduled_daily_report_sent")
    except Exception as e:
        logger.error("scheduled_daily_report_failed", error=str(e))
    finally:
        db.close()
        await telegram.close()

def start_scheduler():
    """Inisialisasi dan jalankan scheduler."""
    scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE)
    
    # Schedule: 07:00 WIB (Asia/Jakarta)
    # Jika settings.TIMEZONE = "Asia/Jakarta"
    scheduler.add_job(
        send_daily_report_job,
        trigger=CronTrigger(hour=7, minute=0),
        id="daily_report",
        name="Daily Telegram Report",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("scheduler_started", timezone=settings.TIMEZONE)
