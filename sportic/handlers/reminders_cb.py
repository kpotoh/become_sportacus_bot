from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from sportic import texts
from sportic.config import Settings
from sportic.db.repositories import UserRepo, WorkoutRepo
from sportic.services.reminders import mark_done, mark_skip, mark_tomorrow
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
        await callback.message.edit_text("Тренировка не найдена.")
        return

    if action == "done":
        streak = await mark_done(session, workout, user)
        text = texts.DONE_BASE.format(name=workout.name, streak=streak)
        text += celebration_extra(streak)
        await callback.message.edit_text(text)
        try:
            await callback.message.answer_dice(emoji="🎰")
        except Exception:
            pass
        return

    if action == "tomorrow":
        await mark_tomorrow(session, workout, user)
        await callback.message.edit_text(texts.POSTPONED.format(name=workout.name))
        return

    if action == "skip":
        await mark_skip(session, workout, user)
        await callback.message.edit_text(texts.SKIPPED.format(name=workout.name))
        return
