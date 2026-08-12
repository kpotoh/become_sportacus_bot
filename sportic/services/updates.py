from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sportic.db.repositories import ReleaseRepo, UserRepo
from sportic.release import VERSION, format_update_message

logger = logging.getLogger(__name__)


async def notify_users_about_update(
    session_factory: async_sessionmaker[AsyncSession],
    bot: Bot,
    *,
    enabled: bool = True,
) -> int:
    """Broadcast release notes once per VERSION. Returns number of successful sends."""
    if not enabled:
        logger.info("Update notifications disabled (UPDATE_NOTIFY=0)")
        return 0

    async with session_factory() as session:
        release_repo = ReleaseRepo(session)
        if await release_repo.was_announced(VERSION):
            logger.info("Release %s already announced", VERSION)
            await session.commit()
            return 0

        users = await UserRepo(session).all_onboarded()
        text = format_update_message()
        sent = 0
        for user in users:
            try:
                await bot.send_message(user.telegram_id, text)
                sent += 1
                await asyncio.sleep(0.05)
            except TelegramRetryAfter as exc:
                await asyncio.sleep(exc.retry_after + 0.5)
                try:
                    await bot.send_message(user.telegram_id, text)
                    sent += 1
                except Exception:
                    logger.exception(
                        "Failed to notify user %s after retry", user.telegram_id
                    )
            except TelegramForbiddenError:
                logger.info("User %s blocked the bot, skip", user.telegram_id)
            except Exception:
                logger.exception("Failed to notify user %s", user.telegram_id)

        await release_repo.mark_announced(VERSION)
        await session.commit()
        logger.info("Announced release %s to %s users", VERSION, sent)
        return sent
