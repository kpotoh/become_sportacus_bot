from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sportic.db.models import LogStatus, User, WorkoutType
from sportic.db.repositories import LogRepo, SlotRepo, UserRepo, WorkoutRepo, user_today
from sportic.keyboards.inline import reminder_actions_kb
from sportic.texts import REMINDER_TEMPLATE, format_streak_line


class ReminderService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], bot: Bot) -> None:
        self.session_factory = session_factory
        self.bot = bot

    async def tick(self) -> None:
        async with self.session_factory() as session:
            users = await UserRepo(session).all_with_slots()
            for user in users:
                if not user.onboarding_done:
                    continue
                await break_overdue_streaks(session, user)
                await self._process_user(session, user)
            await session.commit()

    async def _process_user(self, session: AsyncSession, user: User) -> None:
        tz = ZoneInfo(user.timezone)
        now = datetime.now(tz)
        today = now.date()
        current = now.time().replace(second=0, microsecond=0)

        slot_repo = SlotRepo(session)
        workout_repo = WorkoutRepo(session)
        due = await workout_repo.due_for_user(user)
        if not due:
            return

        for slot in user.notification_slots:
            slot_time = slot.time_local.replace(second=0, microsecond=0)
            if slot_time.hour != current.hour or slot_time.minute != current.minute:
                continue
            if slot.last_fired_on == today:
                continue

            for workout in due:
                text = REMINDER_TEMPLATE.format(
                    name=workout.name,
                    streak_line=format_streak_line(workout.current_streak),
                )
                await self.bot.send_message(
                    chat_id=user.telegram_id,
                    text=text,
                    reply_markup=reminder_actions_kb(workout.id),
                )
            await slot_repo.mark_fired(slot, today)


async def mark_done(
    session: AsyncSession, workout: WorkoutType, user: User
) -> int:
    today = user_today(user.timezone)
    planned = workout.next_due if workout.next_due <= today else today
    await LogRepo(session).add(
        workout,
        planned_date=planned,
        status=LogStatus.done,
        completed_at=datetime.now(ZoneInfo(user.timezone)),
    )
    workout.current_streak = workout.current_streak + 1
    workout.next_due = today + timedelta(days=workout.interval_days)
    await session.flush()
    return workout.current_streak


async def mark_tomorrow(
    session: AsyncSession, workout: WorkoutType, user: User
) -> None:
    today = user_today(user.timezone)
    planned = workout.next_due if workout.next_due <= today else today
    await LogRepo(session).add(
        workout,
        planned_date=planned,
        status=LogStatus.postponed,
    )
    base = max(workout.next_due, today)
    workout.next_due = base + timedelta(days=1)
    await session.flush()


async def mark_skip(
    session: AsyncSession, workout: WorkoutType, user: User
) -> None:
    today = user_today(user.timezone)
    planned = workout.next_due if workout.next_due <= today else today
    await LogRepo(session).add(
        workout,
        planned_date=planned,
        status=LogStatus.skipped,
    )
    workout.current_streak = 0
    workout.next_due = today + timedelta(days=workout.interval_days)
    await session.flush()


async def break_overdue_streaks(session: AsyncSession, user: User) -> None:
    """Reset streak if due day passed without done/postpone (still overdue ≥1 day)."""
    today = user_today(user.timezone)
    for workout in await WorkoutRepo(session).list_active(user.id):
        if workout.current_streak > 0 and (today - workout.next_due).days >= 1:
            workout.current_streak = 0
    await session.flush()
