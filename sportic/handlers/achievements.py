from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from sportic.config import Settings
from sportic.db.repositories import AchievementRepo, UserRepo
from sportic.keyboards.reply import BTN_ACHIEVEMENTS, main_menu
from sportic.services.achievements import format_achievements_list

router = Router(name="achievements")


@router.message(F.text == BTN_ACHIEVEMENTS)
async def show_achievements(
    message: Message, session: AsyncSession, settings: Settings
) -> None:
    user = await UserRepo(session).get_or_create(
        message.from_user.id, settings.default_tz
    )
    unlocked = await AchievementRepo(session).unlocked_map(user.id)
    text = format_achievements_list(unlocked, user.timezone)
    await message.answer(text, reply_markup=main_menu())
