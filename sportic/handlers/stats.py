from __future__ import annotations

from aiogram import F, Router
from aiogram.types import BufferedInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from sportic.config import Settings
from sportic.db.repositories import LogRepo, UserRepo, last_n_days, user_today
from sportic.keyboards.reply import BTN_STATS, main_menu
from sportic.services.charts import chart_week_workouts

router = Router(name="stats")


@router.message(F.text == BTN_STATS)
async def show_stats(
    message: Message, session: AsyncSession, settings: Settings
) -> None:
    user = await UserRepo(session).get_or_create(
        message.from_user.id, settings.default_tz
    )
    today = user_today(user.timezone)
    days = last_n_days(today, 7)
    log_repo = LogRepo(session)

    week_total = await log_repo.count_done_since(user.id, days[0])
    all_total = await log_repo.count_done_since(user.id, since=None)
    week_by_type = await log_repo.done_by_workout_name(user.id, days[0])
    all_by_type = await log_repo.done_by_workout_name(user.id, since=None)
    max_streak = await log_repo.max_streak(user.id)
    series = await log_repo.week_series_by_workout(user.id, days)

    png = chart_week_workouts(series, days, title="Последние 7 дней")
    caption = _caption(week_total, all_total, week_by_type, all_by_type, max_streak)

    await message.answer_photo(
        photo=BufferedInputFile(png, filename="stats.png"),
        caption=caption,
        reply_markup=main_menu(),
    )


def _caption(
    week_total: int,
    all_total: int,
    week_by_type: list[tuple[str, int]],
    all_by_type: list[tuple[str, int]],
    max_streak: int,
) -> str:
    lines = [
        "<b>Статистика</b>",
        f"За неделю: <b>{week_total}</b>",
        f"За всё время: <b>{all_total}</b>",
        f"Макс. текущая серия: <b>{max_streak}</b>",
    ]
    if week_by_type:
        lines.append("\nЗа неделю по типам:")
        for name, cnt in week_by_type:
            lines.append(f"• {name}: {cnt}")
    if all_by_type:
        lines.append("\nЗа всё время по типам:")
        for name, cnt in all_by_type:
            lines.append(f"• {name}: {cnt}")
    return "\n".join(lines)
