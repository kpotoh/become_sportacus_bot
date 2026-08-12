from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from sportic import texts
from sportic.config import Settings
from sportic.db.repositories import UserRepo, WorkoutRepo
from sportic.message_utils import delete_callback_message
from sportic.services.achievements import check_and_unlock, notify_unlocked
from sportic.services.reminders import (
    clear_reminder_message,
    mark_done,
    mark_skip,
    mark_tomorrow,
)
from sportic.services.streaks import celebration_extra

router = Router(name="reminders_cb")


@router.callback_query(F.data.startswith("rem:"))
async def reminder_action(
    callback: CallbackQuery, session: AsyncSession, settings: Settings
) -> None:
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer()
        return
    _, action, wid_s = parts
    workout_id = int(wid_s)
    await callback.answer()

    user = await UserRepo(session).get_or_create(
        callback.from_user.id, settings.default_tz
    )
    workout = await WorkoutRepo(session).get(workout_id)
    if not workout or workout.user_id != user.id or not workout.active:
        await delete_callback_message(callback)
        await callback.message.answer("Тренировка не найдена.")
        return

    bot = callback.bot
    await clear_reminder_message(session, bot, workout)
    await delete_callback_message(callback)

    if action == "done":
        streak = await mark_done(session, workout, user)
        text = texts.DONE_BASE.format(name=workout.name, streak=streak)
        text += celebration_extra(streak)
        await bot.send_message(callback.from_user.id, text)
        unlocked = await check_and_unlock(session, user)
        await notify_unlocked(bot, callback.from_user.id, unlocked)
        if not unlocked:
            try:
                await bot.send_dice(callback.from_user.id, emoji="🎰")
            except Exception:
                pass
        return

    if action == "tomorrow":
        await mark_tomorrow(session, workout, user)
        await bot.send_message(
            callback.from_user.id, texts.POSTPONED.format(name=workout.name)
        )
        return

    if action == "skip":
        await mark_skip(session, workout, user)
        await bot.send_message(
            callback.from_user.id, texts.SKIPPED.format(name=workout.name)
        )
        return
