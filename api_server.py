"""
API сервер для приёма результатов теста с сайта
Работает параллельно с ботом
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from typing import Optional, Dict
from aiohttp import web
from aiogram import Bot

from core.config import Config
from core.container import Container
from core.database import PointsConfig

logger = logging.getLogger(__name__)

# Константы для rate limiting
RATE_LIMIT_REQUESTS = 25  # Максимум запросов
RATE_LIMIT_WINDOW = 60  # За окно в секундах


class RateLimiter:
    """Простой rate limiter на основе временных окон"""

    def __init__(
        self, max_requests: int = RATE_LIMIT_REQUESTS, window: int = RATE_LIMIT_WINDOW
    ):
        self.max_requests = max_requests
        self.window = window
        self.requests: Dict[str, list] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(self, identifier: str) -> bool:
        """Проверка, разрешён ли запрос"""
        async with self._lock:
            now = time.time()
            # Удаляем старые запросы
            self.requests[identifier] = [
                req_time
                for req_time in self.requests[identifier]
                if now - req_time < self.window
            ]

            # Проверяем лимит
            if len(self.requests[identifier]) >= self.max_requests:
                return False

            # Добавляем текущий запрос
            self.requests[identifier].append(now)
            return True


# Глобальный rate limiter
rate_limiter = RateLimiter()


class APIError(Exception):
    """Базовый класс для ошибок API"""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(APIError):
    """Ошибка валидации данных"""

    pass


class DatabaseError(APIError):
    """Ошибка работы с БД"""

    def __init__(self, message: str = "Database error", status_code: int = 500):
        super().__init__(message, status_code)


class RateLimitError(APIError):
    """Ошибка превышения лимита запросов"""

    def __init__(self, message: str = "Rate limit exceeded", status_code: int = 429):
        super().__init__(message, status_code)


def validate_quiz_data(data: dict) -> None:
    """Валидация данных теста"""
    if not isinstance(data, dict):
        raise ValidationError("Invalid data format")

    # Проверка обязательных полей
    if "user_id" not in data:
        raise ValidationError("user_id is required")

    user_id = data.get("user_id")
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValidationError("user_id must be a positive integer")

    # Проверка типа личности
    valid_types = {
        "competing",
        "collaborating",
        "compromising",
        "avoiding",
        "accommodating",
    }
    personality_type = data.get("personality_type")
    if personality_type not in valid_types:
        raise ValidationError(
            f"personality_type must be one of: {', '.join(valid_types)}"
        )

    # Проверка процентов
    percentages = data.get("percentages", {})
    if not isinstance(percentages, dict):
        raise ValidationError("percentages must be a dictionary")

    # Проверка awareness и ras
    awareness = data.get("awareness", 0)
    if not isinstance(awareness, (int, float)) or awareness < -100 or awareness > 100:
        raise ValidationError("awareness must be a number between -100 and 100")

    ras = data.get("ras", 0)
    if not isinstance(ras, (int, float)) or ras < -50 or ras > 50:
        raise ValidationError("ras must be a number between -50 and 50")


async def rate_limit_middleware(app, handler):
    """Middleware для rate limiting по IP адресу"""

    async def middleware_handler(request):
        # Получаем IP адрес клиента
        # Пробуем получить из заголовков (если за прокси)
        client_ip = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or request.headers.get("X-Real-IP", "")
            or request.remote
            or "unknown"
        )

        # Проверяем rate limit
        if not await rate_limiter.is_allowed(client_ip):
            logger.warning(f"[API] Rate limit exceeded for IP: {client_ip}")
            return web.json_response(
                {"error": "Rate limit exceeded. Please try again later."}, status=429
            )

        return await handler(request)

    return middleware_handler


async def error_handler_middleware(app, handler):
    """Middleware для обработки ошибок"""

    async def middleware_handler(request):
        try:
            return await handler(request)
        except APIError as e:
            logger.error(f"[API] API Error: {e.message}")
            return web.json_response({"error": e.message}, status=e.status_code)
        except json.JSONDecodeError:
            logger.error(f"[API] Invalid JSON in request")
            return web.json_response({"error": "Invalid JSON format"}, status=400)
        except Exception as e:
            # Не возвращаем детали ошибки клиенту
            logger.exception(f"[API] Unexpected error: {e}")
            return web.json_response({"error": "Internal server error"}, status=500)

    return middleware_handler


async def handle_quiz_results(request: web.Request):
    """Обработка результатов теста с сайта"""
    data = await request.json()

    # Валидация данных
    validate_quiz_data(data)

    user_id = data["user_id"]
    personality_type = data["personality_type"]
    percentages = data.get("percentages", {})
    awareness = data.get("awareness", 0)
    ras = data.get("ras", 0)

    logger.info(f"[API] Received quiz results from user {user_id}")
    logger.info(
        f"[API] Personality: {personality_type}, Awareness: {awareness}, RAS: {ras}"
    )

    # Получаем бота из app
    bot: Optional[Bot] = request.app.get("bot")
    if not bot:
        logger.error("[API] Bot instance not available")
        raise APIError("Service temporarily unavailable", status_code=503)

    # Получаем БД
    container = Container.get_instance()
    db = container.get_db()

    try:
        # Проверяем онбординг
        onboarding_done = await db.is_onboarding_completed(user_id)
        points_earned = 0

        if not onboarding_done:
            # Завершаем онбординг и начисляем баллы
            total_points = await db.complete_onboarding(user_id)
            points_earned = PointsConfig.ONBOARDING_COMPLETE

            await db.log_event(
                user_id,
                "api_quiz_completed",
                {
                    "personality_type": personality_type,
                    "awareness": awareness,
                    "ras": ras,
                    "points_earned": points_earned,
                },
            )
        else:
            await db.log_event(
                user_id,
                "api_quiz_retake",
                {
                    "personality_type": personality_type,
                    "awareness": awareness,
                    "ras": ras,
                },
            )
            total_points = await db.get_total_points(user_id)

        # Сохраняем результаты теста
        await save_quiz_results(db, user_id, data)

        # Отправляем уведомление в бот (асинхронно, не блокируем ответ)
        asyncio.create_task(
            send_results_notification(
                bot,
                user_id,
                personality_type,
                percentages,
                awareness,
                ras,
                points_earned,
                total_points,
                onboarding_done,
            )
        )

        return web.json_response(
            {
                "success": True,
                "points_earned": points_earned,
                "total_points": total_points,
                "message": "Results saved successfully",
            }
        )

    except Exception as e:
        logger.exception(f"[API] Error processing quiz results for user {user_id}: {e}")
        raise DatabaseError("Failed to process quiz results")


async def save_quiz_results(db, user_id: int, data: dict):
    """Сохранение результатов теста в БД"""
    try:
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

            # Сохраняем в историю
            await conn.execute(
                """
                INSERT INTO user_quiz_history 
                (user_id, personality_type, percentages, awareness, ras, answers)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    user_id,
                    data.get("personality_type"),
                    json.dumps(data.get("percentages", {})),
                    data.get("awareness", 0),
                    data.get("ras", 0),
                    json.dumps(data.get("answers", [])),
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
                    data.get("personality_type"),
                    json.dumps(data.get("percentages", {})),
                    data.get("awareness", 0),
                    data.get("ras", 0),
                    json.dumps(data.get("answers", [])),
                ),
            )
            await conn.commit()

    except Exception as e:
        logger.exception(f"[API] Error saving quiz results: {e}")
        raise DatabaseError("Failed to save quiz results")


async def get_recommended_block(
    personality_type: str, percentages: dict, awareness: int, ras: int
) -> Optional[tuple[int, str]]:
    """
    Определение рекомендуемого блока на основе результатов теста

    Возвращает (block_id, block_title) или None
    """
    try:
        container = Container.get_instance()
        lesson_service = container.get_lesson_service()

        # Получаем все активные блоки
        blocks = await lesson_service.get_all_blocks(include_inactive=False)
        if not blocks:
            return None

        # Сортируем блоки по order
        blocks = sorted(blocks, key=lambda b: b.order)

        # Логика определения рекомендуемого блока на основе personality_type
        # Блоки обычно: 1 = Границы, 2 = Манипуляции, 3 = Пассивная агрессия

        # Определяем рекомендуемый блок на основе стратегии поведения
        # avoiding/accommodating -> проблемы с границами -> Блок "Границы" (обычно блок 1)
        # competing -> агрессивное поведение -> Блок "Манипуляции" (обычно блок 2)
        # compromising/collaborating -> пассивное поведение -> Блок "Пассивная агрессия" (обычно блок 3)

        recommended_block_order = None

        if personality_type in ["avoiding", "accommodating"]:
            # Проблемы с границами - рекомендуем блок "Границы"
            recommended_block_order = 1
        elif personality_type == "competing":
            # Агрессивное поведение - рекомендуем блок "Манипуляции"
            recommended_block_order = 2
        elif personality_type in ["compromising", "collaborating"]:
            # Пассивное поведение - рекомендуем блок "Пассивная агрессия"
            recommended_block_order = 3

        # Ищем блок с нужным order
        recommended_block = None
        if recommended_block_order:
            for block in blocks:
                if block.order == recommended_block_order:
                    recommended_block = block
                    break

        # Если блок не найден, используем первый блок по умолчанию
        if not recommended_block and blocks:
            recommended_block = blocks[0]

        if recommended_block:
            return (recommended_block.id, recommended_block.title)

        return None

    except Exception as e:
        logger.error(f"[API] Error getting recommended block: {e}")
        return None


async def send_results_notification(
    bot: Bot,
    user_id: int,
    personality_type: str,
    percentages: dict,
    awareness: int,
    ras: int,
    points_earned: int,
    total_points: int,
    was_completed: bool,
):
    """Отправка уведомления пользователю в бот"""
    try:
        personality_names = {
            "competing": "Конкуренция 🦈",
            "collaborating": "Сотрудничество 🦉",
            "compromising": "Компромисс 🦊",
            "avoiding": "Избегание 🐢",
            "accommodating": "Адаптивность 🧸",
        }

        personality_name = personality_names.get(personality_type, personality_type)
        awareness_normalized = max(0, min(100, awareness * 10))

        # Получаем рекомендацию по блоку
        recommended_block = await get_recommended_block(
            personality_type, percentages, awareness, ras
        )
        recommendation_text = ""
        if recommended_block:
            block_id, block_title = recommended_block
            recommendation_text = f"\n\nИсходя из ваших результатов, рекомендую начать с Блока «{block_title}» (один из трех модулей)."

        if not was_completed:
            # Первое прохождение
            text = f"""🎉 <b>Тест пройден!</b>

<b>📊 Твои результаты:</b>

🎭 <b>Стратегия:</b> {personality_name}
🧠 <b>Осознанность:</b> {awareness_normalized}/100
💪 <b>Ассертивность:</b> {ras}

<b>+{points_earned} баллов</b> начислено!
💎 Всего баллов: <b>{total_points}</b>{recommendation_text}

Теперь ты готов(а) начать обучение! 🚀"""
        else:
            # Повторное прохождение
            text = f"""📊 <b>Результаты теста обновлены!</b>

🎭 <b>Стратегия:</b> {personality_name}
🧠 <b>Осознанность:</b> {awareness_normalized}/100
💪 <b>Ассертивность:</b> {ras}{recommendation_text}

Результаты сохранены в твоём профиле."""

        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.button(text="📚 К обучению", callback_data="module_learning")
        builder.button(text="👤 Мой профиль", callback_data="my_profile")
        builder.button(text="🏠 Домой", callback_data="home")
        builder.adjust(2, 1)

        await bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode="HTML",
            reply_markup=builder.as_markup(),
        )

        logger.info(f"[API] Sent notification to user {user_id}")

    except Exception as e:
        logger.error(f"[API] Error sending notification to user {user_id}: {e}")


async def handle_health(request: web.Request):
    """Health check endpoint"""
    return web.json_response({"status": "ok"})


def create_app(bot: Optional[Bot] = None) -> web.Application:
    """Создание веб-приложения"""
    app = web.Application()

    # Сохраняем бота в app для доступа из handlers
    if bot:
        app["bot"] = bot

    # CORS middleware
    async def cors_middleware(app, handler):
        async def middleware_handler(request):
            if request.method == "OPTIONS":
                response = web.Response()
            else:
                response = await handler(request)

            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            return response

        return middleware_handler

    # Порядок middleware важен: error_handler должен быть последним
    app.middlewares.append(cors_middleware)
    app.middlewares.append(rate_limit_middleware)
    app.middlewares.append(error_handler_middleware)

    app.router.add_post("/api/quiz/results", handle_quiz_results)
    app.router.add_get("/api/health", handle_health)

    return app


async def start_api_server(bot: Bot, host: str = "0.0.0.0", port: int = 8080):
    """Запуск API сервера"""
    app = create_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info(f"[API] Server started on http://{host}:{port}")
    logger.info(
        f"[API] Rate limit: {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds"
    )
    return runner
