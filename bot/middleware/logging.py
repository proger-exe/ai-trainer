"""
Middleware для логирования событий
"""

import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from core.container import Container

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware для логирования событий"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Логирование события"""
        user_id = None
        event_type = None
        event_data = {}

        if isinstance(event, Message):
            user_id = event.from_user.id
            event_type = "message"
            event_data = {
                "text": event.text[:100] if event.text else None,
                "command": (
                    event.text.split()[0]
                    if event.text and event.text.startswith("/")
                    else None
                ),
            }
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
            event_type = "callback"
            event_data = {"data": event.data}

        if user_id:
            logger.info(f"Event: {event_type}, User: {user_id}, Data: {event_data}")

            # Сохраняем в БД через контейнер
            try:
                container = Container.get_instance()
                db = container.get_db()
                await db.log_event(user_id, event_type, event_data)
            except Exception as e:
                logger.error(f"Failed to log event: {e}")

        return await handler(event, data)
