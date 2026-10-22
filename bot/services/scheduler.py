"""
Планировщик задач для бота
Используется для рассылки Daily Insight и других периодических задач
"""

import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Optional, Callable, Awaitable
import aiosqlite

from core.config import Config

logger = logging.getLogger(__name__)


class Scheduler:
    """Планировщик периодических задач"""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self._running = False
        self._tasks = []

    async def start(self, bot):
        """Запуск планировщика"""
        self._running = True
        self._bot = bot

        # Запускаем задачу проверки инсайтов
        self._tasks.append(asyncio.create_task(self._daily_insight_loop()))

        logger.info("Scheduler started")

    async def stop(self):
        """Остановка планировщика"""
        self._running = False
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()
        logger.info("Scheduler stopped")

    async def _daily_insight_loop(self):
        """Цикл проверки и отправки ежедневных инсайтов"""
        while self._running:
            try:
                current_time = datetime.now()
                logger.debug(
                    f"[Scheduler] Checking for insights at {current_time.strftime('%H:%M')}"
                )

                # Получаем пользователей, которым нужно отправить инсайт
                users_to_notify = await self._get_users_for_insight(current_time)

                if users_to_notify:
                    logger.info(
                        f"[Scheduler] Found {len(users_to_notify)} users to notify"
                    )

                for user_id in users_to_notify:
                    try:
                        await self._send_insight_notification(user_id)
                    except Exception as e:
                        logger.error(
                            f"[Scheduler] Error sending insight to {user_id}: {e}",
                            exc_info=True,
                        )
                        # Продолжаем с другими пользователями даже при ошибке

                # Ждём 5 минут до следующей проверки
                await asyncio.sleep(300)

            except asyncio.CancelledError:
                logger.info("[Scheduler] Daily insight loop cancelled")
                break
            except Exception as e:
                logger.exception(f"[Scheduler] Error in daily insight loop: {e}")
                # Ждём минуту перед следующей попыткой при ошибке
                await asyncio.sleep(60)

    async def _get_users_for_insight(self, current_time: datetime) -> list:
        """Получить пользователей для отправки инсайта"""
        current_hour_minute = current_time.strftime("%H:%M")
        today = current_time.date().isoformat()

        async with aiosqlite.connect(self.db_path) as conn:
            # Получаем пользователей с включёнными уведомлениями,
            # у которых время совпадает и которые ещё не получали инсайт сегодня
            async with conn.execute(
                """
                SELECT u.user_id FROM users u
                LEFT JOIN user_settings s ON u.user_id = s.user_id
                LEFT JOIN user_insights ui ON u.user_id = ui.user_id AND ui.insight_date = ?
                WHERE u.is_active = 1
                AND u.onboarding_completed = 1
                AND (s.daily_insight_enabled IS NULL OR s.daily_insight_enabled = 1)
                AND COALESCE(s.insight_time, '10:00') = ?
                AND ui.id IS NULL
            """,
                (today, current_hour_minute),
            ) as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]

    async def _send_insight_notification(self, user_id: int):
        """Отправить уведомление об инсайте"""
        from bot.handlers.insight import get_todays_insight, init_default_insights
        from bot.keyboards.insight import get_insight_keyboard
        from aiogram.exceptions import TelegramAPIError, TelegramBadRequest

        try:
            # Убедимся, что инсайты инициализированы
            await init_default_insights()

            # Получаем инсайт
            insight, already_earned = await get_todays_insight(user_id)

            if not insight or already_earned:
                logger.debug(
                    f"[Scheduler] No insight to send for user {user_id} (insight={insight is not None}, earned={already_earned})"
                )
                return

            # Формируем сообщение
            text = f"""💡 <b>Daily Insight</b>

{insight.emoji} <b>{insight.title}</b>

{insight.content}

<b>💪 Практика:</b>
<i>{insight.tip}</i>

🎁 <b>+15 баллов</b> за просмотр!"""

            await self._bot.send_message(
                user_id,
                text,
                reply_markup=get_insight_keyboard(insight.id, has_points=True),
            )
            logger.info(f"[Scheduler] Sent daily insight to user {user_id}")

        except TelegramBadRequest as e:
            # Пользователь заблокировал бота или чат не найден
            logger.warning(f"[Scheduler] Cannot send insight to user {user_id}: {e}")
        except TelegramAPIError as e:
            logger.error(
                f"[Scheduler] Telegram API error sending insight to user {user_id}: {e}",
                exc_info=True,
            )
        except Exception as e:
            logger.exception(
                f"[Scheduler] Unexpected error sending insight to user {user_id}: {e}"
            )


# Глобальный экземпляр планировщика
scheduler = Scheduler()
