from __future__ import annotations

from datetime import time

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

TZ_CHOICES = [
    ("Москва", "Europe/Moscow"),
    ("Санкт-Петербург", "Europe/Moscow"),
    ("Екатеринбург", "Asia/Yekaterinburg"),
    ("Новосибирск", "Asia/Novosibirsk"),
    ("Владивосток", "Asia/Vladivostok"),
]

WORKOUT_PRESETS = [
    "Пробежка",
    "Зарядка",
    "Растяжка",
    "Приседания",
    "Теннис",
]

INTERVAL_PRESETS = [1, 2, 3, 7]

TIME_WINDOWS = [
    ("Утром 07:00–10:00", time(7, 0), time(10, 0)),
    ("Днём 12:00–15:00", time(12, 0), time(15, 0)),
    ("Вечером 18:00–21:00", time(18, 0), time(21, 0)),
    ("Весь день 07:00–22:00", time(7, 0), time(22, 0)),
]


def timezone_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for label, tz in TZ_CHOICES:
        builder.button(text=label, callback_data=f"tz:{tz}")
    builder.button(text="Другой…", callback_data="tz:custom")
    builder.adjust(1)
    return builder.as_markup()


def workout_presets_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for name in WORKOUT_PRESETS:
        builder.button(text=name, callback_data=f"wname:{name}")
    builder.button(text="Своё название…", callback_data="wname:custom")
    builder.adjust(2)
    return builder.as_markup()


def interval_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for days in INTERVAL_PRESETS:
        label = f"Каждый день" if days == 1 else f"Раз в {days} дн."
        builder.button(text=label, callback_data=f"wint:{days}")
    builder.button(text="Свой интервал…", callback_data="wint:custom")
    builder.adjust(2)
    return builder.as_markup()


def time_window_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i, (label, _, _) in enumerate(TIME_WINDOWS):
        builder.button(text=label, callback_data=f"wwin:{i}")
    builder.button(text="Свой диапазон…", callback_data="wwin:custom")
    builder.adjust(1)
    return builder.as_markup()


def more_workouts_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить ещё", callback_data="more:yes")
    builder.button(text="К уведомлениям", callback_data="more:no")
    builder.adjust(2)
    return builder.as_markup()


def notifications_setup_kb(slots: list[time]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for t in slots:
        label = t.strftime("%H:%M")
        builder.button(text=f"Удалить {label}", callback_data=f"slotdel:{label}")
    builder.button(text="Добавить слот…", callback_data="slot:add")
    builder.button(text="Готово", callback_data="slot:done")
    builder.adjust(1)
    return builder.as_markup()


def reminder_actions_kb(workout_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Сделал", callback_data=f"rem:done:{workout_id}")
    builder.button(text="Сделаю завтра", callback_data=f"rem:tomorrow:{workout_id}")
    builder.button(text="Пропустить", callback_data=f"rem:skip:{workout_id}")
    builder.adjust(1)
    return builder.as_markup()


def pick_workout_kb(workouts: list[tuple[int, str]], prefix: str) -> InlineKeyboardMarkup:
    """prefix: mark | del"""
    builder = InlineKeyboardBuilder()
    for wid, name in workouts:
        builder.button(text=name, callback_data=f"{prefix}:{wid}")
    builder.button(text="Отмена", callback_data=f"{prefix}:cancel")
    builder.adjust(1)
    return builder.as_markup()


def stats_period_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Месяц", callback_data="stats:month")
    builder.button(text="Год", callback_data="stats:year")
    builder.adjust(2)
    return builder.as_markup()
