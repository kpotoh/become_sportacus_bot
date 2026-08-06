from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sportic.db.models import LogStatus, NotificationSlot, User, WorkoutLog, WorkoutType


def user_today(tz_name: str) -> date:
    return datetime.now(ZoneInfo(tz_name)).date()


def user_now_time(tz_name: str) -> time:
    return datetime.now(ZoneInfo(tz_name)).timetz().replace(tzinfo=None)


class UserRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User)
            .where(User.telegram_id == telegram_id)
            .options(
                selectinload(User.workouts),
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

    async def all_with_slots(self) -> list[User]:
        result = await self.session.execute(
            select(User).options(
                selectinload(User.notification_slots),
                selectinload(User.workouts),
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
            select(WorkoutType).where(WorkoutType.id == workout_id)
        )
        return result.scalar_one_or_none()

    async def deactivate(self, workout: WorkoutType) -> None:
        workout.active = False
        await self.session.flush()

    async def due_for_user(self, user: User) -> list[WorkoutType]:
        today = user_today(user.timezone)
        result = await self.session.execute(
            select(WorkoutType).where(
                WorkoutType.user_id == user.id,
                WorkoutType.active.is_(True),
                WorkoutType.next_due <= today,
            )
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

    async def mark_fired(self, slot: NotificationSlot, on: date) -> None:
        slot.last_fired_on = on
        await self.session.flush()


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

    async def count_done_since(
        self, user_id: int, since: date
    ) -> int:
        result = await self.session.execute(
            select(func.count(WorkoutLog.id))
            .join(WorkoutType)
            .where(
                WorkoutType.user_id == user_id,
                WorkoutLog.status == LogStatus.done,
                WorkoutLog.planned_date >= since,
            )
        )
        return int(result.scalar_one())

    async def done_by_day(
        self, user_id: int, since: date, until: date
    ) -> dict[date, int]:
        result = await self.session.execute(
            select(WorkoutLog.planned_date, func.count(WorkoutLog.id))
            .join(WorkoutType)
            .where(
                WorkoutType.user_id == user_id,
                WorkoutLog.status == LogStatus.done,
                WorkoutLog.planned_date >= since,
                WorkoutLog.planned_date <= until,
            )
            .group_by(WorkoutLog.planned_date)
        )
        return {row[0]: int(row[1]) for row in result.all()}

    async def done_by_month(
        self, user_id: int, since: date, until: date
    ) -> dict[str, int]:
        """Return counts keyed by YYYY-MM."""
        by_day = await self.done_by_day(user_id, since, until)
        months: dict[str, int] = {}
        for d, cnt in by_day.items():
            key = f"{d.year:04d}-{d.month:02d}"
            months[key] = months.get(key, 0) + cnt
        return months

    async def done_by_workout_name(
        self, user_id: int, since: date
    ) -> list[tuple[str, int]]:
        result = await self.session.execute(
            select(WorkoutType.name, func.count(WorkoutLog.id))
            .join(WorkoutLog)
            .where(
                WorkoutType.user_id == user_id,
                WorkoutLog.status == LogStatus.done,
                WorkoutLog.planned_date >= since,
            )
            .group_by(WorkoutType.name)
            .order_by(func.count(WorkoutLog.id).desc())
        )
        return [(row[0], int(row[1])) for row in result.all()]

    async def max_streak(self, user_id: int) -> int:
        result = await self.session.execute(
            select(func.max(WorkoutType.current_streak)).where(
                WorkoutType.user_id == user_id
            )
        )
        value = result.scalar_one()
        return int(value or 0)
