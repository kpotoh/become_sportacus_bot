from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sportic.db.models import LogStatus, User, WorkoutType
from sportic.db.repositories import (
    LogRepo,
    ReminderRepo,
    UserRepo,
    WorkoutRepo,
    user_today,
)
from sportic.keyboards.inline import reminder_actions_kb
from sportic.message_utils import delete_chat_message
from sportic.texts import REMINDER_TEMPLATE, format_streak_line


class ReminderService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], bot: Bot) -> None:
        self.session_factory = session_factory
        self.bot = bot

    async def tick(self) -> None:
        async with self.session_factory() as session:
            users = await UserRepo(session).all_onboarded()
            for user in users:
                await break_overdue_streaks(session, user)
                await self._send_due_reminders(session, user)
                await self._expire_reminders(session, user)
            await session.commit()

    async def _send_due_reminders(self, session: AsyncSession, user: User) -> None:
        tz = ZoneInfo(user.timezone)
        now = datetime.now(tz)
        today = now.date()
        current = now.time().replace(second=0, microsecond=0)

        for workout in await WorkoutRepo(session).due_for_user(user):
            start = workout.time_from.replace(second=0, microsecond=0)
            if start.hour != current.hour or start.minute != current.minute:
                continue
            if workout.last_reminder_on == today:
                continue

            text = REMINDER_TEMPLATE.format(
                name=workout.name,
                streak_line=format_streak_line(workout.current_streak),
                until=workout.time_to.strftime("%H:%M"),
            )
            msg = await self.bot.send_message(
                chat_id=user.telegram_id,
                text=text,
                reply_markup=reminder_actions_kb(workout.id),
            )
            await ReminderRepo(session).set_active(
                workout,
                chat_id=user.telegram_id,
                message_id=msg.message_id,
                sent_on=today,
                expire_time=workout.time_to.replace(second=0, microsecond=0),
            )
            workout.last_reminder_on = today

    async def _expire_reminders(self, session: AsyncSession, user: User) -> None:
        tz = ZoneInfo(user.timezone)
        now = datetime.now(tz)
        today = now.date()
        current = now.time().replace(second=0, microsecond=0)

        for workout in user.workouts:
            if not workout.active or workout.active_reminder is None:
                continue
            rem = workout.active_reminder
            expire = rem.expire_time.replace(second=0, microsecond=0)
            # Expire on the sent day at time_to, or any later day if bot was down
            should_expire = False
            if rem.sent_on < today:
                should_expire = True
            elif rem.sent_on == today and current >= expire:
                should_expire = True
            if not should_expire:
                continue

            await delete_chat_message(self.bot, rem.chat_id, rem.message_id)
            await ReminderRepo(session).clear(workout.id)


async def clear_reminder_message(
    session: AsyncSession, bot: Bot, workout: WorkoutType
) -> None:
    rem = await ReminderRepo(session).clear(workout.id)
    if rem:
        await delete_chat_message(bot, rem.chat_id, rem.message_id)


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
    today = user_today(user.timezone)
    for workout in await WorkoutRepo(session).list_active(user.id):
        if workout.current_streak > 0 and (today - workout.next_due).days >= 1:
            workout.current_streak = 0
    await session.flush()
