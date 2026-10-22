"""
Middleware для проверки прав доступа
"""

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from core.config import Config


class AdminMiddleware(BaseMiddleware):
    """Middleware для проверки прав администратора"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Проверка прав администратора"""
        user_id = None

        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id

        if user_id and user_id not in Config.ADMIN_IDS:
            if isinstance(event, Message):
                await event.answer("❌ У тебя нет доступа к этой команде")
            elif isinstance(event, CallbackQuery):
                await event.answer("❌ У тебя нет доступа", show_alert=True)
            return

        return await handler(event, data)
