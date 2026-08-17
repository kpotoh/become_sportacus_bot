from __future__ import annotations

import enum
from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class LogStatus(str, enum.Enum):
    done = "done"
    skipped = "skipped"
    postponed = "postponed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow")
    onboarding_done: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    workouts: Mapped[list["WorkoutType"]] = relationship(back_populates="user")
    notification_slots: Mapped[list["NotificationSlot"]] = relationship(
        back_populates="user"
    )
    achievements: Mapped[list["UserAchievement"]] = relationship(
        back_populates="user"
    )


class WorkoutType(Base):
    __tablename__ = "workout_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(128))
    interval_days: Mapped[int] = mapped_column(Integer, default=1)
    time_from: Mapped[time] = mapped_column(Time, default=time(7, 0))
    time_to: Mapped[time] = mapped_column(Time, default=time(22, 0))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    started_on: Mapped[date] = mapped_column(Date, default=date.today)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    next_due: Mapped[date] = mapped_column(Date, default=date.today)
    # Last local date when start-of-window reminder was sent
    last_reminder_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="workouts")
    logs: Mapped[list["WorkoutLog"]] = relationship(back_populates="workout")
    active_reminder: Mapped[Optional["ActiveReminder"]] = relationship(
        back_populates="workout", uselist=False
    )


class ActiveReminder(Base):
    """Tracks an open reminder message so it can be deleted at window end or on action."""

    __tablename__ = "active_reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workout_type_id: Mapped[int] = mapped_column(
        ForeignKey("workout_types.id", ondelete="CASCADE"), unique=True
    )
    chat_id: Mapped[int] = mapped_column(BigInteger)
    message_id: Mapped[int] = mapped_column(Integer)
    sent_on: Mapped[date] = mapped_column(Date)
    # Local time of day when the reminder should disappear (22:00)
    expire_time: Mapped[time] = mapped_column(Time)

    workout: Mapped["WorkoutType"] = relationship(back_populates="active_reminder")


class NotificationSlot(Base):
    __tablename__ = "notification_slots"
    __table_args__ = (
        UniqueConstraint("user_id", "time_local", name="uq_user_slot_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    time_local: Mapped[time] = mapped_column(Time)
    last_fired_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    user: Mapped["User"] = relationship(back_populates="notification_slots")


class WorkoutLog(Base):
    __tablename__ = "workout_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workout_type_id: Mapped[int] = mapped_column(
        ForeignKey("workout_types.id", ondelete="CASCADE"), index=True
    )
    planned_date: Mapped[date] = mapped_column(Date, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[LogStatus] = mapped_column(Enum(LogStatus))
    note: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    workout: Mapped["WorkoutType"] = relationship(back_populates="logs")


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    __table_args__ = (
        UniqueConstraint("user_id", "code", name="uq_user_achievement"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(64))
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="achievements")


class AnnouncedRelease(Base):
    """Tracks which app versions were already broadcast to users."""

    __tablename__ = "announced_releases"

    version: Mapped[str] = mapped_column(String(32), primary_key=True)
    announced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
