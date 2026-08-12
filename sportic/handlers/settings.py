from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from sportic import texts
from sportic.config import Settings
from sportic.db.repositories import UserRepo, WorkoutRepo
from sportic.handlers.states import SettingsFlow
from sportic.handlers.workouts import start_add_workout_flow
from sportic.keyboards import inline as ikb
from sportic.keyboards.reply import (
    BTN_ADD_WORKOUT,
    BTN_BACK,
    BTN_CHANGE_TZ,
    BTN_DELETE_WORKOUT,
    BTN_SETTINGS,
    main_menu,
    settings_menu,
)
from sportic.message_utils import delete_callback_message
from sportic.utils import validate_timezone

router = Router(name="settings")


@router.message(F.text == BTN_SETTINGS)
async def open_settings(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.SETTINGS_MENU, reply_markup=settings_menu())


@router.message(F.text == BTN_BACK)
async def back_to_main(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.MAIN_MENU_HINT, reply_markup=main_menu())


@router.message(F.text == BTN_ADD_WORKOUT)
async def settings_add_workout(message: Message, state: FSMContext) -> None:
    await start_add_workout_flow(message, state)


@router.message(F.text == BTN_DELETE_WORKOUT)
async def settings_delete_workout(
    message: Message, session: AsyncSession, settings: Settings
) -> None:
    user = await UserRepo(session).get_or_create(
        message.from_user.id, settings.default_tz
    )
    workouts = await WorkoutRepo(session).list_active(user.id)
    if not workouts:
        await message.answer(texts.MY_WORKOUTS_EMPTY, reply_markup=settings_menu())
        return
    kb = ikb.pick_workout_kb([(w.id, w.name) for w in workouts], prefix="del")
    await message.answer("Какую тренировку удалить?", reply_markup=kb)


@router.message(F.text == BTN_CHANGE_TZ)
async def settings_change_tz(message: Message, state: FSMContext) -> None:
    await state.set_state(SettingsFlow.timezone_custom)
    await message.answer(
        "Выбери пояс или напиши IANA-имя:", reply_markup=ikb.timezone_kb()
    )


@router.callback_query(SettingsFlow.timezone_custom, F.data.startswith("tz:"))
async def settings_tz_cb(
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
        await bot.send_message(callback.from_user.id, texts.ASK_TIMEZONE_CUSTOM)
        return
    user = await UserRepo(session).get_or_create(
        callback.from_user.id, settings.default_tz
    )
    await UserRepo(session).set_timezone(user, value)
    await state.clear()
    await bot.send_message(
        callback.from_user.id,
        f"Часовой пояс: <code>{value}</code>",
        reply_markup=settings_menu(),
    )


@router.message(SettingsFlow.timezone_custom)
async def settings_tz_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    tz = validate_timezone(message.text or "")
    if not tz:
        await message.answer("Не нашёл такой пояс. Пример: <code>Europe/Moscow</code>")
        return
    user = await UserRepo(session).get_or_create(
        message.from_user.id, settings.default_tz
    )
    await UserRepo(session).set_timezone(user, tz)
    await state.clear()
    await message.answer(f"Часовой пояс: <code>{tz}</code>", reply_markup=settings_menu())
