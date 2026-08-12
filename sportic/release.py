"""Bump VERSION and UPDATE_MESSAGE whenever you deploy a user-facing change.

On next bot start, onboarded users get UPDATE_MESSAGE once for this VERSION.
Set UPDATE_NOTIFY=0 in .env to skip broadcasting (useful for local tests).
"""

from __future__ import annotations

# Keep in sync with sportic.__version__
VERSION = "0.2.0"

UPDATE_MESSAGE = (
    "🚀 <b>Sportic обновился</b> (v{version})\n\n"
    "Что нового:\n"
    "• Статистика — график за 7 дней по каждой тренировке\n"
    "• Напоминания в начале окна тренировки, к концу окна сообщение исчезает\n"
    "• Сообщения с кнопками не засоряют чат\n"
    "• Система достижений\n\n"
    "Загляни в «Достижения» и «Статистика»."
)


def format_update_message() -> str:
    return UPDATE_MESSAGE.format(version=VERSION)
