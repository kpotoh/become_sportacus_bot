from __future__ import annotations

import asyncio
import logging

from sportic.bot import create_bot, create_dispatcher
from sportic.config import load_settings
from sportic.db.session import get_session_factory, init_db, init_engine
from sportic.scheduler import setup_scheduler
from sportic.services.reminders import ReminderService


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = load_settings()
    init_engine(settings.database_url)
    await init_db()

    bot = create_bot(settings)
    dp = create_dispatcher(settings)

    reminder_service = ReminderService(get_session_factory(), bot)
    scheduler = setup_scheduler(reminder_service, settings.reminder_check_minutes)
    scheduler.start()

    logging.info("Sportic bot started")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
