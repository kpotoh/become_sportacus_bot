from __future__ import annotations

WELCOME = (
    "Привет! Я Sportic — помогу не забывать про тренировки и держать ударный режим.\n\n"
    "Сначала выбери свой часовой пояс."
)

ASK_TIMEZONE_CUSTOM = (
    "Напиши IANA-название часового пояса, например:\n"
    "<code>Europe/Moscow</code>, <code>Asia/Yekaterinburg</code>, <code>Europe/London</code>"
)

ASK_WORKOUT_NAME = (
    "Какую тренировку добавить?\n"
    "Выбери кнопку или напиши своё название."
)

ASK_INTERVAL = (
    "Как часто делать «{name}»?\n"
    "Выбери интервал в днях между тренировками или введи число."
)

ASK_TIME_WINDOW = (
    "В какое окно дня удобно делать «{name}»?\n"
    "Выбери пресет или введи диапазон вида <code>07:00-10:00</code>."
)

ASK_MORE_WORKOUTS = "Добавить ещё тренировку или закончить настройку?"

ONBOARDING_DONE = (
    "Готово! Настройки сохранены.\n"
    "Напоминание по каждой тренировке придёт в начале её окна "
    "(например в 07:00, если окно 07:00–10:00). "
    "Если к концу окна не отметишь — сообщение исчезнет. Удачи!"
)

MAIN_MENU_HINT = "Главное меню:"

MY_WORKOUTS_EMPTY = "Пока нет активных тренировок. Добавь через Настройки."

SETTINGS_MENU = "Настройки:"

REMINDER_TEMPLATE = (
    "Пора: <b>{name}</b>!\n"
    "{streak_line}\n"
    "Окно до <b>{until}</b>. Не ломай ударный режим — отметь, когда сделаешь."
)

STREAK_LINE = "Ударный режим: <b>{streak}</b> {days_word} подряд"

STREAK_ZERO = "Серия ещё не началась — отличный момент стартовать."

DONE_BASE = "Отлично! «{name}» отмечена. Ударный режим: <b>{streak}</b>."

POSTPONED = "Ок, перенёс «{name}» на завтра. Серия сохранена — не забывай!"

SKIPPED = "Пропустил «{name}». Серия сброшена. Завтра новый шанс!"

UNKNOWN_COMMAND = "Не понял. Пользуйся кнопками меню или /start."


def days_word(n: int) -> str:
    n_abs = abs(n) % 100
    n1 = n_abs % 10
    if 11 <= n_abs <= 19:
        return "дней"
    if n1 == 1:
        return "день"
    if 2 <= n1 <= 4:
        return "дня"
    return "дней"


def is_milestone(streak: int) -> bool:
    if streak in (3, 7, 14, 21, 28):
        return True
    if streak > 28 and (streak - 28) % 14 == 0:
        return True
    return False


def milestone_message(streak: int) -> str:
    if streak == 3:
        return "Три дня подряд — привычка уже цепляется!"
    if streak == 7:
        return "Неделя ударного режима! Так держать."
    if streak == 14:
        return "Две недели без сбоев. Ты в форме!"
    if streak == 21:
        return "Три недели подряд — это уже стиль жизни."
    if streak == 28:
        return "Почти месяц серии! Невероятный темп."
    if streak > 28 and (streak - 28) % 14 == 0:
        weeks = streak // 7
        return f"{streak} дней подряд (~{weeks} нед.) — легендарный ударный режим!"
    return ""


def format_streak_line(streak: int) -> str:
    if streak <= 0:
        return STREAK_ZERO
    return STREAK_LINE.format(streak=streak, days_word=days_word(streak))


def workout_added_message(workout, tz_name: str) -> str:
    from sportic.db.repositories import format_user_dt

    added = format_user_dt(workout.created_at, tz_name)
    return (
        f"Добавлена тренировка <b>{workout.name}</b>\n"
        f"Интервал: каждые {workout.interval_days} дн.\n"
        f"Окно: {workout.time_from.strftime('%H:%M')}–"
        f"{workout.time_to.strftime('%H:%M')}\n"
        f"Когда добавлена: {added}\n"
        f"Напоминание придёт в {workout.time_from.strftime('%H:%M')} "
        f"в дни по плану."
    )
