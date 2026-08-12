from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from sportic.db.models import User
from sportic.db.repositories import (
    AchievementRepo,
    LogRepo,
    last_n_days,
    user_today,
)


@dataclass(frozen=True, slots=True)
class AchievementDef:
    code: str
    title: str
    description: str
    emoji: str
    dice: str | None = None  # Telegram dice emoji on unlock


ACHIEVEMENTS: list[AchievementDef] = [
    AchievementDef(
        "first_done",
        "Первый шаг",
        "Выполни первую тренировку",
        "🌱",
    ),
    AchievementDef(
        "streak_3",
        "Разгон",
        "Ударный режим 3 дня подряд",
        "🔥",
    ),
    AchievementDef(
        "streak_7",
        "Неделя силы",
        "Ударный режим 7 дней подряд",
        "⚡",
        dice="🎯",
    ),
    AchievementDef(
        "streak_14",
        "Две недели",
        "Ударный режим 14 дней подряд",
        "💪",
        dice="🎯",
    ),
    AchievementDef(
        "streak_28",
        "Месяц характера",
        "Ударный режим 28 дней подряд",
        "🏆",
        dice="🎰",
    ),
    AchievementDef(
        "week_full",
        "Идеальная неделя",
        "Хотя бы одна тренировка в каждый из последних 7 дней",
        "📅",
        dice="🎯",
    ),
    AchievementDef(
        "total_10",
        "Десятка",
        "Всего 10 выполненных тренировок",
        "🔟",
    ),
    AchievementDef(
        "total_50",
        "Полтинник",
        "Всего 50 выполненных тренировок",
        "⭐",
        dice="🎰",
    ),
    AchievementDef(
        "total_100",
        "Сотня",
        "Всего 100 выполненных тренировок",
        "💯",
        dice="🎰",
    ),
    AchievementDef(
        "variety_3",
        "Разнообразие",
        "Выполни хотя бы по одной тренировке 3 разных типов",
        "🎨",
    ),
    AchievementDef(
        "comeback",
        "Возвращение",
        "Выполни тренировку после пропуска",
        "♻️",
    ),
]

ACHIEVEMENTS_BY_CODE = {a.code: a for a in ACHIEVEMENTS}


async def check_and_unlock(
    session: AsyncSession,
    user: User,
    *,
    after_skip: bool = False,
) -> list[AchievementDef]:
    """Evaluate catalog and unlock newly earned badges. Returns newly unlocked defs."""
    if after_skip:
        # Comeback is earned on a later done, not on skip itself
        return []

    log_repo = LogRepo(session)
    ach_repo = AchievementRepo(session)
    owned = await ach_repo.codes_for_user(user.id)
    newly: list[AchievementDef] = []

    total = await log_repo.count_done_since(user.id, since=None)
    max_streak = await log_repo.max_streak(user.id)
    variety = await log_repo.count_done_workout_types(user.id)
    today = user_today(user.timezone)
    days = last_n_days(today, 7)
    week_dates = await log_repo.done_dates_any(user.id, days[0], days[-1])
    week_full = all(d in week_dates for d in days)
    had_skip = await log_repo.has_status(user.id, status_skipped=True)

    checks: dict[str, bool] = {
        "first_done": total >= 1,
        "streak_3": max_streak >= 3,
        "streak_7": max_streak >= 7,
        "streak_14": max_streak >= 14,
        "streak_28": max_streak >= 28,
        "week_full": week_full,
        "total_10": total >= 10,
        "total_50": total >= 50,
        "total_100": total >= 100,
        "variety_3": variety >= 3,
        "comeback": had_skip and total >= 1,
    }

    for code, ok in checks.items():
        if not ok or code in owned:
            continue
        definition = ACHIEVEMENTS_BY_CODE[code]
        await ach_repo.unlock(user.id, code)
        newly.append(definition)

    return newly


async def notify_unlocked(
    bot: Bot, chat_id: int, unlocked: list[AchievementDef]
) -> None:
    for ach in unlocked:
        text = (
            f"{ach.emoji} <b>Достижение разблокировано!</b>\n"
            f"<b>{ach.title}</b>\n"
            f"{ach.description}"
        )
        await bot.send_message(chat_id, text)
        if ach.dice:
            try:
                await bot.send_dice(chat_id, emoji=ach.dice)
            except Exception:
                pass


def format_achievements_list(
    unlocked: dict[str, datetime],
    tz_name: str,
) -> str:
    from sportic.db.repositories import format_user_dt

    lines = ["<b>Достижения</b>\n"]
    open_count = 0
    for ach in ACHIEVEMENTS:
        if ach.code in unlocked:
            open_count += 1
            when = format_user_dt(unlocked[ach.code], tz_name)
            lines.append(
                f"{ach.emoji} <b>{ach.title}</b> — {ach.description}\n"
                f"   открыто: {when}"
            )
        else:
            lines.append(f"🔒 <b>{ach.title}</b> — {ach.description}")
    lines.insert(1, f"Открыто: {open_count}/{len(ACHIEVEMENTS)}\n")
    return "\n".join(lines)
