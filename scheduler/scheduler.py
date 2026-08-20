"""
جدولة مهام السحب التلقائي باستخدام APScheduler.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import logger


_scheduler = None


def get_scheduler():
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


def start_scheduler(client):
    """تشغيل الجدولة مع البوت."""
    from workers.draw_worker import process_expired_giveaways
    from config.settings import settings

    scheduler = get_scheduler()

    scheduler.add_job(
        process_expired_giveaways,
        trigger=IntervalTrigger(seconds=settings.SCHEDULER_INTERVAL_SECONDS),
        args=[client],
        id="draw_worker",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "[Scheduler] Started — checking expired giveaways every {}s.",
        settings.SCHEDULER_INTERVAL_SECONDS,
    )


def stop_scheduler():
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown()
        logger.info("[Scheduler] Stopped.")
