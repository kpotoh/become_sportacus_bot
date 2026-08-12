from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

BTN_MY_WORKOUTS = "Мои тренировки"
BTN_MARK_DONE = "Отметить выполненную"
BTN_STATS = "Статистика"
BTN_ACHIEVEMENTS = "Достижения"
BTN_SETTINGS = "Настройки"

BTN_ADD_WORKOUT = "Добавить тренировку"
BTN_CHANGE_TZ = "Часовой пояс"
BTN_DELETE_WORKOUT = "Удалить тренировку"
BTN_BACK = "Назад"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_MY_WORKOUTS), KeyboardButton(text=BTN_MARK_DONE)],
            [KeyboardButton(text=BTN_STATS), KeyboardButton(text=BTN_ACHIEVEMENTS)],
            [KeyboardButton(text=BTN_SETTINGS)],
        ],
        resize_keyboard=True,
    )


def settings_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ADD_WORKOUT), KeyboardButton(text=BTN_DELETE_WORKOUT)],
            [KeyboardButton(text=BTN_CHANGE_TZ)],
            [KeyboardButton(text=BTN_BACK)],
        ],
        resize_keyboard=True,
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
