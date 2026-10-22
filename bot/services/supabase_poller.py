"""
Сервис для проверки новых результатов теста в Supabase
и отправки уведомлений пользователям
"""

import asyncio
import logging
import os
import aiohttp
from typing import Optional
from aiogram import Bot

logger = logging.getLogger(__name__)

# Supabase конфигурация
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


class SupabasePoller:
    """Поллер для проверки новых результатов в Supabase"""

    def __init__(self, bot: Bot, poll_interval: float = 2.0):
        self.bot = bot
        self.poll_interval = poll_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Запуск поллера"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(f"[Supabase] Poller started (interval: {self.poll_interval}s)")

    async def stop(self):
        """Остановка поллера"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[Supabase] Poller stopped")

    async def _poll_loop(self):
        """Основной цикл проверки"""
        while self._running:
            try:
                await self._check_new_results()
            except Exception as e:
                logger.error(f"[Supabase] Poll error: {e}")
            await asyncio.sleep(self.poll_interval)

    async def _check_new_results(self):
        """Проверка новых необработанных результатов"""
        import asyncio

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        }

        try:
            timeout = aiohttp.ClientTimeout(total=10)  # Таймаут 10 секунд
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Получаем необработанные записи
                url = f"{SUPABASE_URL}/rest/v1/quiz_results?processed=eq.false&select=*"
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        logger.warning(
                            f"[Supabase] Unexpected status code {resp.status} when fetching results"
                        )
                        return

                    results = await resp.json()

                    if results:
                        logger.debug(
                            f"[Supabase] Found {len(results)} unprocessed results"
                        )

                    for result in results:
                        await self._process_result(session, headers, result)

        except asyncio.TimeoutError:
            logger.warning("[Supabase] Timeout when checking for new results")
        except aiohttp.ClientError as e:
            logger.error(
                f"[Supabase] Client error when checking for new results: {e}",
                exc_info=True,
            )
        except Exception as e:
            logger.exception(
                f"[Supabase] Unexpected error checking for new results: {e}"
            )

    async def _process_result(
        self, session: aiohttp.ClientSession, headers: dict, result: dict
    ):
        """Обработка одного результата"""
        try:
            user_id = result.get("user_id")
            record_id = result.get("id")

            if not user_id:
                return

            logger.info(f"[Supabase] Processing result for user {user_id}")

            # Отправляем уведомление
            await self._send_notification(user_id, result)

            # Помечаем как обработанное
            import asyncio

            timeout = aiohttp.ClientTimeout(total=5)  # Таймаут 5 секунд для обновления
            update_url = f"{SUPABASE_URL}/rest/v1/quiz_results?id=eq.{record_id}"
            try:
                async with session.patch(
                    update_url,
                    headers=headers,
                    json={"processed": True},
                    timeout=timeout,
                ) as resp:
                    if resp.status == 204:
                        logger.info(
                            f"[Supabase] Marked result {record_id} as processed"
                        )
                    else:
                        logger.error(
                            f"[Supabase] Failed to mark result {record_id} as processed: {resp.status}"
                        )
            except asyncio.TimeoutError:
                logger.warning(
                    f"[Supabase] Timeout marking result {record_id} as processed"
                )
            except aiohttp.ClientError as e:
                logger.error(
                    f"[Supabase] Client error marking result {record_id} as processed: {e}"
                )

            # Сохраняем в локальную БД
            await self._save_to_local_db(user_id, result)

        except Exception as e:
            logger.error(f"[Supabase] Error processing result: {e}")

    async def _send_notification(self, user_id: int, result: dict):
        """Отправка уведомления пользователю"""
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from core.container import Container
        from core.database import PointsConfig

        personality_type = result.get("personality_type", "unknown")
        percentages = result.get("percentages", {})
        awareness = result.get("awareness", 0)
        ras = result.get("ras", 0)

        personality_names = {
            "competing": "Конкуренция 🦈",
            "collaborating": "Сотрудничество 🦉",
            "compromising": "Компромисс 🦊",
            "avoiding": "Избегание 🐢",
            "accommodating": "Адаптивность 🧸",
        }

        personality_name = personality_names.get(personality_type, personality_type)
        awareness_normalized = max(0, min(100, awareness * 10))

        # Проверяем онбординг и начисляем баллы
        container = Container.get_instance()
        db = container.get_db()

        onboarding_done = await db.is_onboarding_completed(user_id)
        points_earned = 0
        total_points = 0

        if not onboarding_done:
            total_points = await db.complete_onboarding(user_id)
            points_earned = PointsConfig.ONBOARDING_COMPLETE

            await db.log_event(
                user_id,
                "supabase_quiz_completed",
                {
                    "personality_type": personality_type,
                    "awareness": awareness,
                    "ras": ras,
                    "points_earned": points_earned,
                },
            )

            text = f"""🎉 <b>Тест пройден!</b>

<b>📊 Твои результаты:</b>

🎭 <b>Стратегия:</b> {personality_name}
🧠 <b>Осознанность:</b> {awareness_normalized}/100
💪 <b>Ассертивность:</b> {ras}

<b>+{points_earned} баллов</b> начислено!
💎 Всего баллов: <b>{total_points}</b>

Теперь ты готов(а) начать обучение! 🚀"""
        else:
            await db.log_event(
                user_id,
                "supabase_quiz_retake",
                {
                    "personality_type": personality_type,
                    "awareness": awareness,
                    "ras": ras,
                },
            )

            text = f"""📊 <b>Результаты теста обновлены!</b>

🎭 <b>Стратегия:</b> {personality_name}
🧠 <b>Осознанность:</b> {awareness_normalized}/100
💪 <b>Ассертивность:</b> {ras}

Результаты сохранены в твоём профиле."""

        builder = InlineKeyboardBuilder()
        builder.button(text="📚 К обучению", callback_data="module_learning")
        builder.button(text="👤 Мой профиль", callback_data="my_profile")
        builder.button(text="🏠 Домой", callback_data="home")
        builder.adjust(2, 1)

        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="HTML",
                reply_markup=builder.as_markup(),
            )
            logger.info(f"[Supabase] Sent notification to user {user_id}")
        except Exception as e:
            logger.error(f"[Supabase] Failed to send notification to {user_id}: {e}")

    async def _save_to_local_db(self, user_id: int, result: dict):
        """Сохранение результатов в локальную БД"""
        import json
        from core.container import Container

        try:
            container = Container.get_instance()
            db = container.get_db()

            async with db.get_connection() as conn:
                # Таблица для последнего результата
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_quiz_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER UNIQUE,
                        personality_type TEXT,
                        percentages TEXT,
                        awareness INTEGER,
                        ras INTEGER,
                        answers TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Таблица истории
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_quiz_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        personality_type TEXT,
                        percentages TEXT,
                        awareness INTEGER,
                        ras INTEGER,
                        answers TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                percentages = result.get("percentages", {})
                answers = result.get("answers", [])

                # Сохраняем в историю
                await conn.execute(
                    """
                    INSERT INTO user_quiz_history 
                    (user_id, personality_type, percentages, awareness, ras, answers)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        user_id,
                        result.get("personality_type"),
                        (
                            json.dumps(percentages)
                            if isinstance(percentages, dict)
                            else percentages
                        ),
                        result.get("awareness", 0),
                        result.get("ras", 0),
                        json.dumps(answers) if isinstance(answers, list) else answers,
                    ),
                )

                # Обновляем последний результат
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO user_quiz_results 
                    (user_id, personality_type, percentages, awareness, ras, answers, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                    (
                        user_id,
                        result.get("personality_type"),
                        (
                            json.dumps(percentages)
                            if isinstance(percentages, dict)
                            else percentages
                        ),
                        result.get("awareness", 0),
                        result.get("ras", 0),
                        json.dumps(answers) if isinstance(answers, list) else answers,
                    ),
                )
                await conn.commit()

            logger.info(f"[Supabase] Saved results to local DB for user {user_id}")
        except Exception as e:
            logger.error(f"[Supabase] Error saving to local DB: {e}")


# Глобальный экземпляр поллера
supabase_poller: Optional[SupabasePoller] = None


async def start_supabase_poller(bot: Bot, poll_interval: float = 2.0):
    """Запуск Supabase поллера"""
    global supabase_poller
    if not (SUPABASE_URL and SUPABASE_KEY):
        logger.info("[Supabase] SUPABASE_URL/SUPABASE_KEY not set, poller disabled")
        return None
    supabase_poller = SupabasePoller(bot, poll_interval)
    await supabase_poller.start()
    return supabase_poller


async def stop_supabase_poller():
    """Остановка Supabase поллера"""
    global supabase_poller
    if supabase_poller:
        await supabase_poller.stop()
