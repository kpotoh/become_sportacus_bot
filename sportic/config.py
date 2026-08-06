from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    default_tz: str
    database_url: str
    reminder_check_minutes: int


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "BOT_TOKEN is not set. Copy .env.example to .env and put your token from @BotFather."
        )
    return Settings(
        bot_token=token,
        default_tz=os.getenv("DEFAULT_TZ", "Europe/Moscow").strip(),
        database_url=os.getenv(
            "DATABASE_URL", f"sqlite+aiosqlite:///{ROOT_DIR / 'sportic.db'}"
        ).strip(),
        reminder_check_minutes=int(os.getenv("REMINDER_CHECK_MINUTES", "1")),
    )
