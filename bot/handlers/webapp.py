"""
Обработчики данных из Telegram WebApp (тест на сайте)
"""

import json
import logging
import hmac
import hashlib
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, WebAppInfo
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramAPIError

from core.config import Config
from core.container import Container
from core.database import PointsConfig
from bot.keyboards import get_main_keyboard
from bot.keyboards.onboarding_extended import get_webapp_results_keyboard

router = Router()
logger = logging.getLogger(__name__)

# Допустимые значения для валидации
VALID_PERSONALITY_TYPES = {
    "competing",
    "collaborating",
    "compromising",
    "avoiding",
    "accommodating",
}


def verify_telegram_webapp_data(init_data: str, bot_token: str) -> bool:
    """
    Проверка подписи initData от Telegram WebApp.
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    try:
        # Парсим init_data
        parsed_data = dict(chunk.split("=", 1) for chunk in init_data.split("&"))

        # Извлекаем hash
        received_hash = parsed_data.pop("hash", None)
        if not received_hash:
            return False

        # Сортируем и формируем строку для проверки
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed_data.items())
        )

        # Создаём секретный ключ
        secret_key = hmac.new(
            b"WebAppData", bot_token.encode(), hashlib.sha256
        ).digest()

        # Вычисляем hash
        calculated_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(calculated_hash, received_hash)
    except (ValueError, KeyError, AttributeError) as e:
        logger.debug(f"[WebApp] Error verifying webapp data: {e}")
        return False
    except Exception as e:
        logger.warning(f"[WebApp] Unexpected error verifying webapp data: {e}")
        return False


def validate_quiz_data(data: dict) -> tuple[bool, str]:
    """Валидация данных теста"""
    # Проверяем наличие обязательных полей
    required_fields = ["personality_type", "percentages", "awareness", "ras"]
    for field in required_fields:
        if field not in data:
            return False, f"Отсутствует поле: {field}"

    # Проверяем тип личности
    if data["personality_type"] not in VALID_PERSONALITY_TYPES:
        return False, "Некорректный тип личности"

    # Проверяем проценты
    percentages = data.get("percentages", {})
    if not isinstance(percentages, dict):
        return False, "Некорректный формат процентов"

    # Проверяем диапазоны
    awareness = data.get("awareness", 0)
    if not isinstance(awareness, (int, float)) or awareness < -100 or awareness > 100:
        return False, "Некорректное значение осознанности"

    ras = data.get("ras", 0)
    if not isinstance(ras, (int, float)) or ras < -50 or ras > 50:
        return False, "Некорректное значение ассертивности"

    return True, "OK"


@router.message(Command("test"))
async def cmd_test(message: Message):
    """Команда для быстрого доступа к тесту"""
    user_id = message.from_user.id

    if not Config.ONBOARDING_WEBAPP_URL:
        await message.answer("❌ Тест временно недоступен")
        return

    container = Container.get_instance()
    db = container.get_db()
    onboarding_done = await db.is_onboarding_completed(user_id)

    # Формируем URL с user_id для WebApp
    test_url = (
        f"{Config.ONBOARDING_WEBAPP_URL}&user_id={user_id}"
        if "?" in Config.ONBOARDING_WEBAPP_URL
        else f"{Config.ONBOARDING_WEBAPP_URL}?user_id={user_id}"
    )

    builder = InlineKeyboardBuilder()
    builder.button(
        text="📝 Пройти тест" if not onboarding_done else "📝 Пройти тест снова",
        web_app=WebAppInfo(url=test_url),
    )
    builder.button(text="📊 История тестов", callback_data="quiz_history")
    builder.button(text="🏠 Домой", callback_data="home")
    builder.adjust(1)

    if not onboarding_done:
        text = """📝 <b>Экспресс-тест на осознанность в коммуникации</b>

Тест из 15 вопросов поможет определить:
• 🎭 Твою стратегию поведения в конфликтах
• 🧠 Уровень осознанности в общении
• 💪 Степень ассертивности

За прохождение ты получишь <b>+50 баллов</b>! 🎁"""
    else:
        text = """📝 <b>Пройти тест снова</b>

Ты уже проходил(а) этот тест, но можешь пройти его снова, чтобы:
• Отследить изменения в своём стиле общения
• Проверить прогресс после обучения
• Получить актуальные результаты

<i>Баллы за повторное прохождение не начисляются.</i>"""

    await message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "quiz_history")
async def callback_quiz_history(callback: CallbackQuery):
    """Показать историю прохождений теста"""
    user_id = callback.from_user.id

    container = Container.get_instance()
    db = container.get_db()

    history = await get_quiz_history(db, user_id, limit=10)

    if not history:
        await callback.answer("У тебя пока нет истории тестов", show_alert=True)
        return

    personality_names = {
        "competing": "🦈 Конкуренция",
        "collaborating": "🦉 Сотрудничество",
        "compromising": "🦊 Компромисс",
        "avoiding": "🐢 Избегание",
        "accommodating": "🧸 Адаптивность",
    }

    text = "📊 <b>История прохождений теста</b>\n\n"

    for i, item in enumerate(history, 1):
        ptype = item["personality_type"]
        pname = personality_names.get(ptype, ptype)
        awareness = max(0, min(100, item["awareness"] * 10))
        ras = item["ras"]
        date = item["created_at"][:10] if item["created_at"] else "—"

        text += f"<b>{i}.</b> {date}\n"
        text += f"   {pname}\n"
        text += f"   🧠 {awareness}/100 | 💪 RAS: {ras}\n\n"

    # Формируем URL с user_id для WebApp
    user_id = callback.from_user.id
    test_url = (
        f"{Config.ONBOARDING_WEBAPP_URL}&user_id={user_id}"
        if "?" in Config.ONBOARDING_WEBAPP_URL
        else f"{Config.ONBOARDING_WEBAPP_URL}?user_id={user_id}"
    )

    builder = InlineKeyboardBuilder()
    if Config.ONBOARDING_WEBAPP_URL:
        builder.button(text="📝 Пройти тест снова", web_app=WebAppInfo(url=test_url))
    builder.button(text="🏠 Домой", callback_data="home")
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "webapp_results_done")
async def callback_webapp_results_done(callback: CallbackQuery):
    """Возврат в бот после показа результатов WebApp-теста."""
    await callback.answer("Сверните это окно и вернитесь в тг-бот", show_alert=True)
    await callback.message.answer("🏠 Главное меню", reply_markup=get_main_keyboard())


@router.message(F.web_app_data)
async def handle_webapp_data(message: Message, state: FSMContext):
    """Обработка данных из WebApp (результаты теста)"""
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "Пользователь"

    try:
        # Парсим данные из WebApp
        data = json.loads(message.web_app_data.data)
        action = data.get("action")

        if action == "tma_auth":
            # Логируем авторизацию TMA
            container = Container.get_instance()
            db = container.get_db()

            user_data = data.get("user_data", {})
            platform = data.get("platform", "unknown")
            version = data.get("version", "unknown")

            await db.log_event(
                user_id,
                "tma_auth",
                {
                    "user_id": user_id,
                    "username": user_data.get("username"),
                    "first_name": user_data.get("first_name"),
                    "platform": platform,
                    "version": version,
                },
            )

            # Не отправляем сообщение пользователю, просто логируем
            logger.info(
                f"[WebApp] TMA Auth: User {user_id} ({user_data.get('first_name', 'Unknown')}) opened WebApp from {platform}"
            )

        elif action == "quiz_complete":
            # Проверяем подпись initData (если есть)
            init_data = data.get("init_data")
            if init_data and Config.TELEGRAM_BOT_TOKEN:
                if not verify_telegram_webapp_data(
                    init_data, Config.TELEGRAM_BOT_TOKEN
                ):
                    # Логируем подозрительную активность, но не блокируем
                    container = Container.get_instance()
                    db = container.get_db()
                    await db.log_event(
                        user_id, "webapp_invalid_signature", {"action": action}
                    )

            # Валидируем данные
            is_valid, error_msg = validate_quiz_data(data)
            if not is_valid:
                await message.answer(
                    f"⚠️ Ошибка данных теста: {error_msg}\nПопробуй пройти тест ещё раз."
                )
                return

            await handle_quiz_complete(message, data, user_id, first_name, state)
        elif action == "share":
            # Обработка шаринга результатов
            await message.answer("📤 Результаты готовы к отправке!")
        else:
            await message.answer("❓ Неизвестное действие из WebApp")

    except json.JSONDecodeError as e:
        logger.error(
            f"[WebApp] JSON decode error for user {user_id}: {e}", exc_info=True
        )
        await message.answer("❌ Ошибка обработки данных из теста. Попробуй ещё раз.")
    except TelegramAPIError as e:
        logger.error(
            f"[WebApp] Telegram API error for user {user_id}: {e}", exc_info=True
        )
        await message.answer("❌ Ошибка отправки сообщения. Попробуй позже.")
    except Exception as e:
        logger.exception(
            f"[WebApp] Unexpected error handling webapp data for user {user_id}: {e}"
        )
        await message.answer(
            "❌ Произошла ошибка. Попробуй позже или обратись в поддержку."
        )


async def handle_quiz_complete(
    message: Message, data: dict, user_id: int, first_name: str, state: FSMContext
):
    """Обработка завершения теста на сайте"""
    try:
        container = Container.get_instance()
        db = container.get_db()

        # Логируем TMA данные
        tma_data = data.get("tma", {})
        if tma_data:
            platform = tma_data.get("platform", "unknown")
            version = tma_data.get("version", "unknown")
            color_scheme = tma_data.get("color_scheme", "unknown")
            user_data = tma_data.get("user_data", {})

            logger.info(f"[WebApp] TMA Quiz Complete: User {user_id} ({first_name})")
            logger.debug(
                f"[WebApp] Platform: {platform}, Version: {version}, Theme: {color_scheme}"
            )
            if user_data:
                logger.debug(f"[WebApp] Username: @{user_data.get('username', 'N/A')}")

        # Извлекаем результаты
        personality_type = data.get("personality_type", "collaborating")
        percentages = data.get("percentages", {})
        awareness = data.get("awareness", 0)
        ras = data.get("ras", 0)
        answers = data.get("answers", [])

        # Валидация данных
        if not personality_type or personality_type not in VALID_PERSONALITY_TYPES:
            logger.warning(
                f"[WebApp] Invalid personality_type for user {user_id}: {personality_type}"
            )
            personality_type = "collaborating"  # Fallback

        # Названия типов личности на русском
        personality_names = {
            "competing": "Конкуренция 🦈",
            "collaborating": "Сотрудничество 🦉",
            "compromising": "Компромисс 🦊",
            "avoiding": "Избегание 🐢",
            "accommodating": "Адаптивность 🧸",
        }

        personality_name = personality_names.get(personality_type, personality_type)

        # Проверяем, не пройден ли уже онбординг
        if not await db.is_onboarding_completed(user_id):
            # Завершаем онбординг и начисляем баллы
            total_points = await db.complete_onboarding(user_id)
            points_earned = PointsConfig.ONBOARDING_COMPLETE

            # Логируем событие
            await db.log_event(
                user_id,
                "webapp_quiz_completed",
                {
                    "personality_type": personality_type,
                    "percentages": percentages,
                    "awareness": awareness,
                    "ras": ras,
                    "points_earned": points_earned,
                },
            )

            # Сохраняем результаты теста в профиль пользователя
            await save_quiz_results(db, user_id, data)

            # Формируем сообщение с результатами
            text = f"""🎉 <b>Поздравляем, {first_name}!</b>

Ты успешно прошёл(ла) тест на осознанность в коммуникации!

<b>📊 Твои результаты:</b>

🎭 <b>Преобладающая стратегия:</b> {personality_name}

<b>Распределение стратегий:</b>
"""
            # Добавляем проценты по типам
            type_labels = {
                "competing": "🦈 Конкуренция",
                "collaborating": "🦉 Сотрудничество",
                "compromising": "🦊 Компромисс",
                "avoiding": "🐢 Избегание",
                "accommodating": "🧸 Адаптивность",
            }

            for type_key, label in type_labels.items():
                percent = percentages.get(type_key, 0)
                bar = "█" * (percent // 10) + "░" * (10 - percent // 10)
                text += f"├ {label}: {bar} {percent}%\n"

            # Добавляем осознанность и ассертивность
            awareness_normalized = max(0, min(100, awareness * 10))
            text += f"""
🧠 <b>Осознанность:</b> {awareness_normalized}/100
💪 <b>Ассертивность (RAS):</b> {ras}

<b>+{points_earned} баллов</b> начислено!
💎 Всего баллов: <b>{total_points}</b>

Исходя из ваших результатов, рекомендую начать с Блока «Границы» (один из трех модулей).

Теперь ты готов(а) начать обучение! 🚀"""

            await message.answer(text, reply_markup=get_webapp_results_keyboard())
        else:
            # Онбординг уже пройден - просто показываем результаты
            await db.log_event(
                user_id,
                "webapp_quiz_retake",
                {
                    "personality_type": personality_type,
                    "percentages": percentages,
                    "awareness": awareness,
                    "ras": ras,
                },
            )

            # Обновляем результаты теста
            await save_quiz_results(db, user_id, data)

            text = f"""📊 <b>Результаты теста</b>

🎭 <b>Преобладающая стратегия:</b> {personality_name}

<b>Распределение стратегий:</b>
"""
            type_labels = {
                "competing": "🦈 Конкуренция",
                "collaborating": "🦉 Сотрудничество",
                "compromising": "🦊 Компромисс",
                "avoiding": "🐢 Избегание",
                "accommodating": "🧸 Адаптивность",
            }

            for type_key, label in type_labels.items():
                percent = percentages.get(type_key, 0)
                bar = "█" * (percent // 10) + "░" * (10 - percent // 10)
                text += f"├ {label}: {bar} {percent}%\n"

            awareness_normalized = max(0, min(100, awareness * 10))
            text += f"""
🧠 <b>Осознанность:</b> {awareness_normalized}/100
💪 <b>Ассертивность (RAS):</b> {ras}

Результаты сохранены в твоём профиле!

Исходя из ваших результатов, рекомендую начать с Блока «Границы» (один из трех модулей)."""

            await message.answer(text, reply_markup=get_webapp_results_keyboard())

    except TelegramAPIError as e:
        logger.error(
            f"[WebApp] Telegram API error sending quiz results to user {user_id}: {e}",
            exc_info=True,
        )
        try:
            await message.answer("❌ Ошибка отправки результатов. Попробуй позже.")
        except Exception:
            pass  # Если не можем отправить сообщение, просто логируем
    except Exception as e:
        logger.exception(
            f"[WebApp] Unexpected error handling quiz complete for user {user_id}: {e}"
        )
        try:
            await message.answer(
                "❌ Произошла ошибка при обработке результатов. Попробуй позже."
            )
        except Exception:
            pass  # Если не можем отправить сообщение, просто логируем


async def save_quiz_results(db, user_id: int, data: dict):
    """Сохранение результатов теста в БД (последний результат + история)"""
    try:
        async with db.get_connection() as conn:
            # Таблица для последнего результата (быстрый доступ)
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
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """
            )

            # Таблица истории всех прохождений
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
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """
            )

            # Сохраняем в историю (всегда новая запись)
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
        logger.exception(f"[WebApp] Error saving quiz results for user {user_id}: {e}")
        raise


async def get_quiz_history(db, user_id: int, limit: int = 5) -> list:
    """Получение истории прохождений теста"""
    try:
        async with db.get_connection() as conn:
            async with conn.execute(
                """SELECT personality_type, awareness, ras, created_at 
                   FROM user_quiz_history 
                   WHERE user_id = ? 
                   ORDER BY created_at DESC 
                   LIMIT ?""",
                (user_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "personality_type": row[0],
                        "awareness": row[1] or 0,
                        "ras": row[2] or 0,
                        "created_at": row[3],
                    }
                    for row in rows
                ]
    except Exception as e:
        logger.error(
            f"[WebApp] Error getting quiz history for user {user_id}: {e}",
            exc_info=True,
        )
        return []
