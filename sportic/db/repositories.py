from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sportic.db.models import (
    ActiveReminder,
    AnnouncedRelease,
    LogStatus,
    NotificationSlot,
    User,
    UserAchievement,
    WorkoutLog,
    WorkoutType,
)


def user_today(tz_name: str) -> date:
    return datetime.now(ZoneInfo(tz_name)).date()


def user_now_time(tz_name: str) -> time:
    return datetime.now(ZoneInfo(tz_name)).timetz().replace(tzinfo=None)


def format_user_dt(dt: datetime | None, tz_name: str) -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        local = dt
    else:
        local = dt.astimezone(ZoneInfo(tz_name))
    return local.strftime("%d.%m.%Y %H:%M")


class UserRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User)
            .where(User.telegram_id == telegram_id)
            .options(
                selectinload(User.workouts).selectinload(WorkoutType.active_reminder),
                selectinload(User.notification_slots),
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, telegram_id: int, default_tz: str) -> User:
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            return user
        user = User(telegram_id=telegram_id, timezone=default_tz)
        self.session.add(user)
        await self.session.flush()
        return user

    async def set_timezone(self, user: User, tz: str) -> None:
        user.timezone = tz
        await self.session.flush()

    async def mark_onboarding_done(self, user: User) -> None:
        user.onboarding_done = True
        await self.session.flush()

    async def all_onboarded(self) -> list[User]:
        result = await self.session.execute(
            select(User)
            .where(User.onboarding_done.is_(True))
            .options(
                selectinload(User.workouts).selectinload(WorkoutType.active_reminder),
            )
        )
        return list(result.scalars().unique().all())


class WorkoutRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self,
        user: User,
        name: str,
        interval_days: int,
        time_from: time,
        time_to: time,
    ) -> WorkoutType:
        today = user_today(user.timezone)
        workout = WorkoutType(
            user_id=user.id,
            name=name.strip(),
            interval_days=interval_days,
            time_from=time_from,
            time_to=time_to,
            started_on=today,
            next_due=today,
            current_streak=0,
            active=True,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(workout)
        await self.session.flush()
        return workout

    async def list_active(self, user_id: int) -> list[WorkoutType]:
        result = await self.session.execute(
            select(WorkoutType)
            .where(WorkoutType.user_id == user_id, WorkoutType.active.is_(True))
            .order_by(WorkoutType.id)
        )
        return list(result.scalars().all())

    async def get(self, workout_id: int) -> WorkoutType | None:
        result = await self.session.execute(
            select(WorkoutType)
            .where(WorkoutType.id == workout_id)
            .options(selectinload(WorkoutType.active_reminder))
        )
        return result.scalar_one_or_none()

    async def deactivate(self, workout: WorkoutType) -> None:
        workout.active = False
        await self.session.flush()

    async def due_for_user(self, user: User) -> list[WorkoutType]:
        today = user_today(user.timezone)
        result = await self.session.execute(
            select(WorkoutType)
            .where(
                WorkoutType.user_id == user.id,
                WorkoutType.active.is_(True),
                WorkoutType.next_due <= today,
            )
            .options(selectinload(WorkoutType.active_reminder))
        )
        return list(result.scalars().all())


class ReminderRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def set_active(
        self,
        workout: WorkoutType,
        chat_id: int,
        message_id: int,
        sent_on: date,
        expire_time: time,
    ) -> ActiveReminder:
        existing = await self.get_for_workout(workout.id)
        if existing:
            existing.chat_id = chat_id
            existing.message_id = message_id
            existing.sent_on = sent_on
            existing.expire_time = expire_time
            await self.session.flush()
            return existing
        rem = ActiveReminder(
            workout_type_id=workout.id,
            chat_id=chat_id,
            message_id=message_id,
            sent_on=sent_on,
            expire_time=expire_time,
        )
        self.session.add(rem)
        workout.last_reminder_on = sent_on
        await self.session.flush()
        return rem

    async def get_for_workout(self, workout_id: int) -> ActiveReminder | None:
        result = await self.session.execute(
            select(ActiveReminder).where(ActiveReminder.workout_type_id == workout_id)
        )
        return result.scalar_one_or_none()

    async def clear(self, workout_id: int) -> ActiveReminder | None:
        rem = await self.get_for_workout(workout_id)
        if rem:
            await self.session.delete(rem)
            await self.session.flush()
        return rem

    async def all_active(self) -> list[ActiveReminder]:
        result = await self.session.execute(
            select(ActiveReminder).options(selectinload(ActiveReminder.workout))
        )
        return list(result.scalars().all())


class SlotRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_user(self, user_id: int) -> list[NotificationSlot]:
        result = await self.session.execute(
            select(NotificationSlot)
            .where(NotificationSlot.user_id == user_id)
            .order_by(NotificationSlot.time_local)
        )
        return list(result.scalars().all())

    async def ensure_defaults(self, user: User) -> None:
        existing = await self.list_for_user(user.id)
        if existing:
            return
        for t in (time(9, 0), time(18, 0)):
            self.session.add(NotificationSlot(user_id=user.id, time_local=t))
        await self.session.flush()

    async def add(self, user: User, t: time) -> NotificationSlot | None:
        existing = await self.list_for_user(user.id)
        if any(s.time_local == t for s in existing):
            return None
        slot = NotificationSlot(user_id=user.id, time_local=t)
        self.session.add(slot)
        await self.session.flush()
        return slot

    async def remove(self, user: User, t: time) -> bool:
        result = await self.session.execute(
            select(NotificationSlot).where(
                NotificationSlot.user_id == user.id,
                NotificationSlot.time_local == t,
            )
        )
        slot = result.scalar_one_or_none()
        if not slot:
            return False
        await self.session.delete(slot)
        await self.session.flush()
        return True


class LogRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self,
        workout: WorkoutType,
        planned_date: date,
        status: LogStatus,
        completed_at: datetime | None = None,
        note: str | None = None,
    ) -> WorkoutLog:
        log = WorkoutLog(
            workout_type_id=workout.id,
            planned_date=planned_date,
            status=status,
            completed_at=completed_at,
            note=note,
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def count_done_since(self, user_id: int, since: date | None = None) -> int:
        stmt = (
            select(func.count(WorkoutLog.id))
            .join(WorkoutType)
            .where(
                WorkoutType.user_id == user_id,
                WorkoutLog.status == LogStatus.done,
            )
        )
        if since is not None:
            stmt = stmt.where(WorkoutLog.planned_date >= since)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def done_dates_for_workout(
        self, workout_id: int, since: date, until: date
    ) -> set[date]:
        result = await self.session.execute(
            select(WorkoutLog.planned_date).where(
                WorkoutLog.workout_type_id == workout_id,
                WorkoutLog.status == LogStatus.done,
                WorkoutLog.planned_date >= since,
                WorkoutLog.planned_date <= until,
            )
        )
        return set(result.scalars().all())

    async def week_series_by_workout(
        self, user_id: int, days: list[date]
    ) -> dict[str, list[int]]:
        """For each active workout: list of 0/1 aligned with days."""
        if not days:
            return {}
        since, until = days[0], days[-1]
        workouts = await WorkoutRepo(self.session).list_active(user_id)
        series: dict[str, list[int]] = {}
        for w in workouts:
            done = await self.done_dates_for_workout(w.id, since, until)
            series[w.name] = [1 if d in done else 0 for d in days]
        return series

    async def done_by_workout_name(
        self, user_id: int, since: date | None = None
    ) -> list[tuple[str, int]]:
        stmt = (
            select(WorkoutType.name, func.count(WorkoutLog.id))
            .join(WorkoutLog)
            .where(
                WorkoutType.user_id == user_id,
                WorkoutLog.status == LogStatus.done,
            )
            .group_by(WorkoutType.name)
            .order_by(func.count(WorkoutLog.id).desc())
        )
        if since is not None:
            stmt = stmt.where(WorkoutLog.planned_date >= since)
        result = await self.session.execute(stmt)
        return [(row[0], int(row[1])) for row in result.all()]

    async def max_streak(self, user_id: int) -> int:
        result = await self.session.execute(
            select(func.max(WorkoutType.current_streak)).where(
                WorkoutType.user_id == user_id
            )
        )
        value = result.scalar_one()
        return int(value or 0)

    async def count_done_workout_types(self, user_id: int) -> int:
        result = await self.session.execute(
            select(func.count(func.distinct(WorkoutType.id)))
            .join(WorkoutLog)
            .where(
                WorkoutType.user_id == user_id,
                WorkoutLog.status == LogStatus.done,
            )
        )
        return int(result.scalar_one())

    async def done_dates_any(
        self, user_id: int, since: date, until: date
    ) -> set[date]:
        result = await self.session.execute(
            select(WorkoutLog.planned_date)
            .join(WorkoutType)
            .where(
                WorkoutType.user_id == user_id,
                WorkoutLog.status == LogStatus.done,
                WorkoutLog.planned_date >= since,
                WorkoutLog.planned_date <= until,
            )
        )
        return set(result.scalars().all())

    async def has_status(self, user_id: int, *, status_skipped: bool = False) -> bool:
        status = LogStatus.skipped if status_skipped else LogStatus.done
        result = await self.session.execute(
            select(func.count(WorkoutLog.id))
            .join(WorkoutType)
            .where(
                WorkoutType.user_id == user_id,
                WorkoutLog.status == status,
            )
        )
        return int(result.scalar_one()) > 0


class AchievementRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def codes_for_user(self, user_id: int) -> set[str]:
        result = await self.session.execute(
            select(UserAchievement.code).where(UserAchievement.user_id == user_id)
        )
        return set(result.scalars().all())

    async def unlocked_map(self, user_id: int) -> dict[str, datetime]:
        result = await self.session.execute(
            select(UserAchievement).where(UserAchievement.user_id == user_id)
        )
        return {row.code: row.unlocked_at for row in result.scalars().all()}

    async def unlock(self, user_id: int, code: str) -> UserAchievement:
        row = UserAchievement(
            user_id=user_id,
            code=code,
            unlocked_at=datetime.now(timezone.utc),
        )
        self.session.add(row)
        await self.session.flush()
        return row


class ReleaseRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def was_announced(self, version: str) -> bool:
        result = await self.session.execute(
            select(AnnouncedRelease).where(AnnouncedRelease.version == version)
        )
        return result.scalar_one_or_none() is not None

    async def mark_announced(self, version: str) -> None:
        if await self.was_announced(version):
            return
        self.session.add(
            AnnouncedRelease(
                version=version,
                announced_at=datetime.now(timezone.utc),
            )
        )
        await self.session.flush()


def last_n_days(today: date, n: int = 7) -> list[date]:
    return [today - timedelta(days=n - 1 - i) for i in range(n)]
