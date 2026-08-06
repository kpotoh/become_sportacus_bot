from __future__ import annotations

from datetime import timedelta

from aiogram import F, Router
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from sportic import texts
from sportic.config import Settings
from sportic.db.repositories import LogRepo, UserRepo, user_today
from sportic.keyboards.inline import stats_period_kb
from sportic.keyboards.reply import BTN_STATS, main_menu
from sportic.services.charts import chart_daily_counts, chart_monthly_counts

router = Router(name="stats")


@router.message(F.text == BTN_STATS)
async def stats_menu(message: Message) -> None:
    await message.answer(texts.STATS_PICK_PERIOD, reply_markup=stats_period_kb())


@router.callback_query(F.data.startswith("stats:"))
async def stats_period(
    callback: CallbackQuery, session: AsyncSession, settings: Settings
) -> None:
    period = callback.data.split(":", 1)[1]
    await callback.answer()
    user = await UserRepo(session).get_or_create(
        callback.from_user.id, settings.default_tz
    )
    today = user_today(user.timezone)
    log_repo = LogRepo(session)

    if period == "month":
        since = today - timedelta(days=29)
        until = today
        total = await log_repo.count_done_since(user.id, since)
        by_type = await log_repo.done_by_workout_name(user.id, since)
        max_streak = await log_repo.max_streak(user.id)
        day_counts = await log_repo.done_by_day(user.id, since, until)
        png = chart_daily_counts(day_counts, "Тренировки за 30 дней")
        caption = _caption("месяц (30 дней)", total, by_type, max_streak)
    else:
        since = today - timedelta(days=364)
        until = today
        total = await log_repo.count_done_since(user.id, since)
        by_type = await log_repo.done_by_workout_name(user.id, since)
        max_streak = await log_repo.max_streak(user.id)
        month_counts = await log_repo.done_by_month(user.id, since, until)
        png = chart_monthly_counts(month_counts, "Тренировки за год")
        caption = _caption("год", total, by_type, max_streak)

    await callback.message.answer_photo(
        photo=BufferedInputFile(png, filename="stats.png"),
        caption=caption,
        reply_markup=main_menu(),
    )


def _caption(
    period_label: str,
    total: int,
    by_type: list[tuple[str, int]],
    max_streak: int,
) -> str:
    lines = [
        f"Статистика за {period_label}",
        f"Всего выполнено: <b>{total}</b>",
        f"Макс. текущая серия: <b>{max_streak}</b>",
    ]
    if by_type:
        lines.append("По типам:")
        for name, cnt in by_type:
            lines.append(f"• {name}: {cnt}")
    return "\n".join(lines)
