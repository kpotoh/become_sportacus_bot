"""Bump VERSION and UPDATE_MESSAGE whenever you deploy a user-facing change.

On next bot start, onboarded users get UPDATE_MESSAGE once for this VERSION.
Set UPDATE_NOTIFY=0 in .env to skip broadcasting (useful for local tests).
"""

from __future__ import annotations

# Keep in sync with sportic.__version__
VERSION = "0.2.1"

UPDATE_MESSAGE = (
    "🚀 <b>Sportic обновился</b> (v{version})\n\n"
    "Что нового:\n"
    "• Кнопки «Сделал / Сделаю завтра / Пропустить» больше не исчезают "
    "в конце окна тренировки — сообщение живёт до <b>22:00</b>.\n"
    "Так удобнее отметить тренировку вечером."
)


def format_update_message() -> str:
    return UPDATE_MESSAGE.format(version=VERSION)
