from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from sportic import texts
from sportic.config import Settings
from sportic.db.repositories import UserRepo, WorkoutRepo
from sportic.handlers.states import Onboarding
from sportic.keyboards import inline as ikb
from sportic.keyboards.reply import main_menu
from sportic.message_utils import delete_callback_message
from sportic.utils import parse_positive_int, parse_time_range, validate_timezone

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    await state.clear()
    user = await UserRepo(session).get_or_create(
        message.from_user.id, settings.default_tz
    )
    if user.onboarding_done:
        await message.answer(texts.MAIN_MENU_HINT, reply_markup=main_menu())
        return

    await state.set_state(Onboarding.timezone)
    await message.answer(texts.WELCOME, reply_markup=ikb.timezone_kb())


@router.callback_query(Onboarding.timezone, F.data.startswith("tz:"))
async def onboarding_tz(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, settings: Settings
) -> None:
    value = callback.data.split(":", 1)[1]
    await callback.answer()
    await delete_callback_message(callback)
    bot = callback.bot
    if value == "custom":
        await state.set_state(Onboarding.timezone_custom)
        await bot.send_message(callback.from_user.id, texts.ASK_TIMEZONE_CUSTOM)
        return

    user = await UserRepo(session).get_or_create(
        callback.from_user.id, settings.default_tz
    )
    await UserRepo(session).set_timezone(user, value)
    await state.set_state(Onboarding.workout_name)
    await bot.send_message(
        callback.from_user.id,
        texts.ASK_WORKOUT_NAME,
        reply_markup=ikb.workout_presets_kb(),
    )


@router.message(Onboarding.timezone_custom)
async def onboarding_tz_custom(
    message: Message, state: FSMContext, session: AsyncSession, settings: Settings
) -> None:
    tz = validate_timezone(message.text or "")
    if not tz:
        await message.answer("Не нашёл такой пояс. Пример: <code>Europe/Moscow</code>")
        return
    user = await UserRepo(session).get_or_create(
        message.from_user.id, settings.default_tz
    )
    await UserRepo(session).set_timezone(user, tz)
    await state.set_state(Onboarding.workout_name)
    await message.answer(texts.ASK_WORKOUT_NAME, reply_markup=ikb.workout_presets_kb())


@router.callback_query(Onboarding.workout_name, F.data.startswith("wname:"))
async def onboarding_wname_cb(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":", 1)[1]
    await callback.answer()
    await delete_callback_message(callback)
    bot = callback.bot
    if value == "custom":
        await state.set_state(Onboarding.workout_name_custom)
        await bot.send_message(callback.from_user.id, "Напиши название тренировки:")
        return
    await state.update_data(workout_name=value)
    await state.set_state(Onboarding.workout_interval)
    await bot.send_message(
        callback.from_user.id,
        texts.ASK_INTERVAL.format(name=value),
        reply_markup=ikb.interval_kb(),
    )


@router.message(Onboarding.workout_name)
@router.message(Onboarding.workout_name_custom)
async def onboarding_wname_text(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("Название не может быть пустым.")
        return
    await state.update_data(workout_name=name)
    await state.set_state(Onboarding.workout_interval)
    await message.answer(
        texts.ASK_INTERVAL.format(name=name), reply_markup=ikb.interval_kb()
    )


@router.callback_query(Onboarding.workout_interval, F.data.startswith("wint:"))
async def onboarding_interval_cb(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":", 1)[1]
    await callback.answer()
    await delete_callback_message(callback)
    bot = callback.bot
    if value == "custom":
        await state.set_state(Onboarding.workout_interval_custom)
        await bot.send_message(
            callback.from_user.id,
            "Введи число дней между тренировками (например 4):",
        )
        return
    data = await state.get_data()
    await state.update_data(interval_days=int(value))
    await state.set_state(Onboarding.workout_window)
    await bot.send_message(
        callback.from_user.id,
        texts.ASK_TIME_WINDOW.format(name=data["workout_name"]),
        reply_markup=ikb.time_window_kb(),
    )


@router.message(Onboarding.workout_interval)
@router.message(Onboarding.workout_interval_custom)
async def onboarding_interval_text(message: Message, state: FSMContext) -> None:
    days = parse_positive_int(message.text or "")
    if days is None:
        await message.answer("Нужно целое число ≥ 1.")
        return
    data = await state.get_data()
    await state.update_data(interval_days=days)
    await state.set_state(Onboarding.workout_window)
    await message.answer(
        texts.ASK_TIME_WINDOW.format(name=data["workout_name"]),
        reply_markup=ikb.time_window_kb(),
    )


@router.callback_query(Onboarding.workout_window, F.data.startswith("wwin:"))
async def onboarding_window_cb(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    value = callback.data.split(":", 1)[1]
    await callback.answer()
    await delete_callback_message(callback)
    bot = callback.bot
    if value == "custom":
        await state.set_state(Onboarding.workout_window_custom)
        await bot.send_message(
            callback.from_user.id,
            "Введи диапазон, например <code>07:00-10:00</code>",
        )
        return
    idx = int(value)
    _, t_from, t_to = ikb.TIME_WINDOWS[idx]
    workout = await _save_onboarding_workout(
        callback.from_user.id, state, session, settings, t_from, t_to
    )
    user = await UserRepo(session).get_or_create(
        callback.from_user.id, settings.default_tz
    )
    await bot.send_message(
        callback.from_user.id,
        texts.workout_added_message(workout, user.timezone),
    )
    await state.set_state(Onboarding.more_workouts)
    await bot.send_message(
        callback.from_user.id,
        texts.ASK_MORE_WORKOUTS,
        reply_markup=ikb.more_workouts_kb(),
    )


@router.message(Onboarding.workout_window)
@router.message(Onboarding.workout_window_custom)
async def onboarding_window_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    parsed = parse_time_range(message.text or "")
    if not parsed:
        await message.answer("Формат: <code>07:00-10:00</code> (начало раньше конца).")
        return
    t_from, t_to = parsed
    workout = await _save_onboarding_workout(
        message.from_user.id, state, session, settings, t_from, t_to
    )
    user = await UserRepo(session).get_or_create(
        message.from_user.id, settings.default_tz
    )
    await message.answer(texts.workout_added_message(workout, user.timezone))
    await state.set_state(Onboarding.more_workouts)
    await message.answer(texts.ASK_MORE_WORKOUTS, reply_markup=ikb.more_workouts_kb())


async def _save_onboarding_workout(
    telegram_id: int,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
    t_from,
    t_to,
):
    data = await state.get_data()
    user = await UserRepo(session).get_or_create(telegram_id, settings.default_tz)
    return await WorkoutRepo(session).add(
        user,
        name=data["workout_name"],
        interval_days=int(data["interval_days"]),
        time_from=t_from,
        time_to=t_to,
    )


@router.callback_query(Onboarding.more_workouts, F.data.startswith("more:"))
async def onboarding_more(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    value = callback.data.split(":", 1)[1]
    await callback.answer()
    await delete_callback_message(callback)
    bot = callback.bot
    if value == "yes":
        await state.set_state(Onboarding.workout_name)
        await bot.send_message(
            callback.from_user.id,
            texts.ASK_WORKOUT_NAME,
            reply_markup=ikb.workout_presets_kb(),
        )
        return

    user = await UserRepo(session).get_or_create(
        callback.from_user.id, settings.default_tz
    )
    await UserRepo(session).mark_onboarding_done(user)
    await state.clear()
    await bot.send_message(
        callback.from_user.id,
        texts.ONBOARDING_DONE,
        reply_markup=main_menu(),
    )
