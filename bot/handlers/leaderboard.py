"""
Обработчики лидерборда
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from core.container import Container
from bot.keyboards.common import get_home_keyboard

router = Router()


@router.callback_query(F.data == "leaderboard")
async def callback_leaderboard(callback: CallbackQuery):
    """Показать лидерборд"""
    container = Container.get_instance()
    points_service = container.get_points_service()
    user_service = container.get_user_service()

    leaderboard = await points_service.get_leaderboard(limit=20)

    if not leaderboard:
        text = "📊 <b>Лидерборд</b>\n\nПока никого нет в рейтинге!"
        await callback.message.edit_text(text, reply_markup=get_home_keyboard())
        await callback.answer()
        return

    text = "🏆 <b>Лидерборд</b>\n\n"

    medals = ["🥇", "🥈", "🥉"]
    for i, entry in enumerate(leaderboard[:20], 1):
        user_id = entry["user_id"]
        total_points = entry["total_points"]

        user = await user_service.get_user(user_id)
        username = user.first_name if user else f"User {user_id}"

        medal = medals[i - 1] if i <= 3 else f"{i}."
        text += f"{medal} {username}: <b>{total_points}</b> баллов\n"

    await callback.message.edit_text(text, reply_markup=get_home_keyboard())
    await callback.answer()
