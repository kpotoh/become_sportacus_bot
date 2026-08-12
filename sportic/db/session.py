from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from sportic.db.models import Base

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str) -> None:
    global _engine, _session_factory
    _engine = create_async_engine(database_url, echo=False)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def init_db() -> None:
    if _engine is None:
        raise RuntimeError("Engine is not initialized")
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_sqlite)


def _migrate_sqlite(sync_conn) -> None:
    """Add columns introduced after first release (SQLite has no auto-alter)."""
    rows = sync_conn.execute(text("PRAGMA table_info(workout_types)")).fetchall()
    if not rows:
        return
    cols = {row[1] for row in rows}
    if "last_reminder_on" not in cols:
        sync_conn.execute(
            text("ALTER TABLE workout_types ADD COLUMN last_reminder_on DATE")
        )


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Session factory is not initialized")
    return _session_factory


async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
