from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from sportic.config import Settings
from sportic.db.session import get_session_factory
from sportic.handlers import (
    achievements,
    reminders_cb,
    settings as settings_handlers,
    start,
    stats,
    workouts,
)
from sportic.middlewares import DbSessionMiddleware


def create_bot(settings: Settings) -> Bot:
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher(settings: Settings) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp["settings"] = settings
    session_factory = get_session_factory()
    dp.update.middleware(DbSessionMiddleware(session_factory))

    @dp.update.outer_middleware()
    async def inject_settings(handler, event, data):
        data["settings"] = settings
        return await handler(event, data)

    dp.include_router(start.router)
    dp.include_router(workouts.router)
    dp.include_router(settings_handlers.router)
    dp.include_router(reminders_cb.router)
    dp.include_router(stats.router)
    dp.include_router(achievements.router)
    return dp
