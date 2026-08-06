from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from sportic import texts
from sportic.config import Settings
from sportic.db.repositories import UserRepo, WorkoutRepo
from sportic.handlers.states import AddWorkout
from sportic.keyboards import inline as ikb
from sportic.keyboards.reply import (
    BTN_MARK_DONE,
    BTN_MY_WORKOUTS,
    main_menu,
)
from sportic.services.reminders import mark_done
from sportic.services.streaks import celebration_extra
from sportic.utils import parse_positive_int, parse_time_range

router = Router(name="workouts")


@router.message(F.text == BTN_MY_WORKOUTS)
async def my_workouts(
    message: Message, session: AsyncSession, settings: Settings
) -> None:
    user = await UserRepo(session).get_or_create(
        message.from_user.id, settings.default_tz
    )
    workouts = await WorkoutRepo(session).list_active(user.id)
    if not workouts:
        await message.answer(texts.MY_WORKOUTS_EMPTY, reply_markup=main_menu())
        return
    lines = []
    for w in workouts:
        lines.append(
            f"• <b>{w.name}</b> — каждые {w.interval_days} дн., "
            f"{w.time_from.strftime('%H:%M')}–{w.time_to.strftime('%H:%M')}\n"
            f"  следующая: {w.next_due.isoformat()}, серия: {w.current_streak}"
        )
    await message.answer("\n".join(lines), reply_markup=main_menu())


@router.message(F.text == BTN_MARK_DONE)
async def mark_done_pick(
    message: Message, session: AsyncSession, settings: Settings
) -> None:
    user = await UserRepo(session).get_or_create(
        message.from_user.id, settings.default_tz
    )
    workouts = await WorkoutRepo(session).list_active(user.id)
    if not workouts:
        await message.answer(texts.MY_WORKOUTS_EMPTY, reply_markup=main_menu())
        return
    kb = ikb.pick_workout_kb([(w.id, w.name) for w in workouts], prefix="mark")
    await message.answer("Какую тренировку отметить?", reply_markup=kb)


@router.callback_query(F.data.startswith("mark:"))
async def mark_done_cb(
    callback: CallbackQuery, session: AsyncSession, settings: Settings
) -> None:
    value = callback.data.split(":", 1)[1]
    await callback.answer()
    if value == "cancel":
        await callback.message.edit_text("Отменено.")
        return
    workout_id = int(value)
    user = await UserRepo(session).get_or_create(
        callback.from_user.id, settings.default_tz
    )
    workout = await WorkoutRepo(session).get(workout_id)
    if not workout or workout.user_id != user.id or not workout.active:
        await callback.message.answer("Тренировка не найдена.")
        return
    streak = await mark_done(session, workout, user)
    text = texts.DONE_BASE.format(name=workout.name, streak=streak)
    text += celebration_extra(streak)
    await callback.message.edit_text(text)
    # Celebration animation
    try:
        await callback.message.answer_dice(emoji="🎰")
    except Exception:
        pass


async def start_add_workout_flow(message: Message, state: FSMContext) -> None:
    await state.set_state(AddWorkout.name)
    await message.answer(texts.ASK_WORKOUT_NAME, reply_markup=ikb.workout_presets_kb())


@router.callback_query(AddWorkout.name, F.data.startswith("wname:"))
async def add_wname_cb(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":", 1)[1]
    await callback.answer()
    if value == "custom":
        await state.set_state(AddWorkout.name_custom)
        await callback.message.answer("Напиши название тренировки:")
        return
    await state.update_data(workout_name=value)
    await state.set_state(AddWorkout.interval)
    await callback.message.answer(
        texts.ASK_INTERVAL.format(name=value), reply_markup=ikb.interval_kb()
    )


@router.message(AddWorkout.name)
@router.message(AddWorkout.name_custom)
async def add_wname_text(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("Название не может быть пустым.")
        return
    await state.update_data(workout_name=name)
    await state.set_state(AddWorkout.interval)
    await message.answer(
        texts.ASK_INTERVAL.format(name=name), reply_markup=ikb.interval_kb()
    )


@router.callback_query(AddWorkout.interval, F.data.startswith("wint:"))
async def add_interval_cb(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":", 1)[1]
    await callback.answer()
    if value == "custom":
        await state.set_state(AddWorkout.interval_custom)
        await callback.message.answer("Введи число дней между тренировками:")
        return
    data = await state.get_data()
    await state.update_data(interval_days=int(value))
    await state.set_state(AddWorkout.window)
    await callback.message.answer(
        texts.ASK_TIME_WINDOW.format(name=data["workout_name"]),
        reply_markup=ikb.time_window_kb(),
    )


@router.message(AddWorkout.interval)
@router.message(AddWorkout.interval_custom)
async def add_interval_text(message: Message, state: FSMContext) -> None:
    days = parse_positive_int(message.text or "")
    if days is None:
        await message.answer("Нужно целое число ≥ 1.")
        return
    data = await state.get_data()
    await state.update_data(interval_days=days)
    await state.set_state(AddWorkout.window)
    await message.answer(
        texts.ASK_TIME_WINDOW.format(name=data["workout_name"]),
        reply_markup=ikb.time_window_kb(),
    )


@router.callback_query(AddWorkout.window, F.data.startswith("wwin:"))
async def add_window_cb(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    value = callback.data.split(":", 1)[1]
    await callback.answer()
    if value == "custom":
        await state.set_state(AddWorkout.window_custom)
        await callback.message.answer(
            "Введи диапазон, например <code>07:00-10:00</code>"
        )
        return
    idx = int(value)
    _, t_from, t_to = ikb.TIME_WINDOWS[idx]
    await _save_workout(callback.from_user.id, state, session, settings, t_from, t_to)
    await state.clear()
    await callback.message.answer("Тренировка добавлена.", reply_markup=main_menu())


@router.message(AddWorkout.window)
@router.message(AddWorkout.window_custom)
async def add_window_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    parsed = parse_time_range(message.text or "")
    if not parsed:
        await message.answer("Формат: <code>07:00-10:00</code>")
        return
    t_from, t_to = parsed
    await _save_workout(message.from_user.id, state, session, settings, t_from, t_to)
    await state.clear()
    await message.answer("Тренировка добавлена.", reply_markup=main_menu())


async def _save_workout(
    telegram_id: int,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
    t_from,
    t_to,
) -> None:
    data = await state.get_data()
    user = await UserRepo(session).get_or_create(telegram_id, settings.default_tz)
    await WorkoutRepo(session).add(
        user,
        name=data["workout_name"],
        interval_days=int(data["interval_days"]),
        time_from=t_from,
        time_to=t_to,
    )


@router.callback_query(F.data.startswith("del:"))
async def delete_workout_cb(
    callback: CallbackQuery, session: AsyncSession, settings: Settings
) -> None:
    value = callback.data.split(":", 1)[1]
    await callback.answer()
    if value == "cancel":
        await callback.message.edit_text("Отменено.")
        return
    workout_id = int(value)
    user = await UserRepo(session).get_or_create(
        callback.from_user.id, settings.default_tz
    )
    workout = await WorkoutRepo(session).get(workout_id)
    if not workout or workout.user_id != user.id:
        await callback.message.answer("Тренировка не найдена.")
        return
    await WorkoutRepo(session).deactivate(workout)
    await callback.message.edit_text(f"«{workout.name}» удалена.")
