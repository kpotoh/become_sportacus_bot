from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from sportic.services.reminders import ReminderService


def setup_scheduler(
    reminder_service: ReminderService, check_minutes: int
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        reminder_service.tick,
        trigger="interval",
        minutes=max(1, check_minutes),
        id="reminder_tick",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    return scheduler
