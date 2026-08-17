# Sportic — Telegram-бот напоминаний о тренировках

Бот помогает регулярно тренироваться: собирает план (виды тренировок, интервал, окно времени), шлёт напоминания, считает ударный режим (streak) и показывает статистику с графиками.

## Стек

- Python 3.12+
- [aiogram 3](https://docs.aiogram.dev/)
- SQLite (SQLAlchemy async + aiosqlite)
- APScheduler
- matplotlib

## Быстрый старт

1. Создай бота у [@BotFather](https://t.me/BotFather) и скопируй токен.

2. Установи зависимости:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Конфиг:

```bash
cp .env.example .env
# отредактируй BOT_TOKEN в .env
```

4. Запуск:

```bash
python -m sportic
```

## Запуск на сервере как systemd-сервис

Подходит для VPS / домашнего сервера с Linux (systemd). Бот будет подниматься при загрузке и перезапускаться при падении.

### 1. Размести код на сервере

```bash
# пример путей — подставь свои
sudo mkdir -p /opt/sportic
sudo chown "$USER":"$USER" /opt/sportic
cd /opt/sportic
# скопируй репозиторий сюда (git clone / rsync / scp)

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
nano .env   # укажи BOT_TOKEN
```

Рекомендуется абсолютный путь к БД в `.env`, чтобы сервис не зависел от рабочей директории:

```env
BOT_TOKEN=123456:ABC-DEF
DATABASE_URL=sqlite+aiosqlite:////opt/sportic/sportic.db
DEFAULT_TZ=Europe/Moscow
```

### 2. Unit-файл systemd

Создай файл `/etc/systemd/system/sportic.service`:

```ini
[Unit]
Description=Sportic Telegram bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=YOUR_USER
Group=YOUR_USER
WorkingDirectory=/opt/sportic
EnvironmentFile=/opt/sportic/.env
ExecStart=/opt/sportic/.venv/bin/python -m sportic
Restart=on-failure
RestartSec=5
# логи в journald
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Замени `YOUR_USER` на пользователя, от которого крутится бот (не `root`, если можно).

### 3. Включи и запусти

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sportic.service
sudo systemctl status sportic.service
```

Полезные команды:

```bash
# логи в реальном времени
sudo journalctl -u sportic.service -f

# перезапуск после правок кода или .env
sudo systemctl restart sportic.service

# остановка
sudo systemctl stop sportic.service
```

После обновления кода на сервере:

```bash
cd /opt/sportic
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart sportic.service
```

## Возможности

- Онбординг: часовой пояс → тренировки (название, дни между, окно времени)
- Напоминание по каждой тренировке в начале её окна; неотвеченное сообщение удаляется в 22:00
- Кнопки: **Сделал** / **Сделаю завтра** / **Пропустить** (сообщение с кнопками удаляется после действия)
- Ударный режим с порогами 3, 7, 14, 21, 28, далее каждые 14 дней
- Анимация при выполнении (Telegram dice 🎰)
- Статистика: линейный график за 7 дней (одна линия на тренировку) + числа за неделю и за всё время
- Достижения (бейджи) с уведомлениями и dice на крупных порогах
- Меню: мои тренировки, отметить, статистика, достижения, настройки

## Переменные окружения

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен от BotFather (обязательно) |
| `DEFAULT_TZ` | Часовой пояс по умолчанию (`Europe/Moscow`) |
| `DATABASE_URL` | URL SQLite, по умолчанию `sqlite+aiosqlite:///./sportic.db` |
| `REMINDER_CHECK_MINUTES` | Интервал проверки окон тренировок (минуты), по умолчанию `1` |
| `UPDATE_NOTIFY` | Рассылать анонс обновления при старте (`1` / `0`), по умолчанию `1` |

## Анонс обновления пользователям

При каждом релизе с пользовательскими изменениями:

1. Подними `VERSION` в [`sportic/release.py`](sportic/release.py) и `__version__` в [`sportic/__init__.py`](sportic/__init__.py).
2. Отредактируй текст `UPDATE_MESSAGE` в `sportic/release.py`.
3. Задеплой и перезапусти сервис (`systemctl restart sportic`).

При старте бот один раз отправит сообщение всем пользователям с пройденным онбордингом. Повторный рестарт той же версии повторно не шлёт (факт рассылки хранится в БД). Для локальных тестов: `UPDATE_NOTIFY=0`.
