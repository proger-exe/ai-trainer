"""
Общие обработчики (start, home, help)
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest

from core.config import Config
from core.container import Container
from core.bridge import bridge
from bot.keyboards import get_main_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    try:
        logger.info(f"[Common] /start command from user {user_id}")

        # Добавляем пользователя в БД
        container = Container.get_instance()
        user_service = container.get_user_service()
        from bot.models.user import UserCreate

        await user_service.create_or_update_user(
            UserCreate(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
        )

        # Логируем событие
        db = container.get_db()
        try:
            await db.log_event(user_id, "start", {"username": username})
        except Exception as e:
            logger.warning(
                f"[Common] Failed to log start event for user {user_id}: {e}"
            )

        # Очищаем состояние
        await state.clear()

        # Проверяем, прошёл ли пользователь онбординг
        if not await db.is_onboarding_completed(user_id):
            # Показываем приветствие с предложением пройти расширенный онбординг
            from bot.keyboards.onboarding_extended import (
                get_onboarding_welcome_keyboard,
            )

            welcome_text = f"""👋 Привет{", " + first_name if first_name else ""}! 

Я — твой ИИ-тренажёр коммуникаций.

Я помогу тебе:
• 🛡️ Устанавливать и защищать границы
• 🎭 Распознавать манипуляции
• 🤝 Эффективно вести переговоры
• 😤 Справляться с токсичными собеседниками

За прохождение знакомства ты получишь <b>+50 баллов</b> и персональную рекомендацию! 🎁

Давай познакомимся? 🙂"""

            await message.answer(
                welcome_text, reply_markup=get_onboarding_welcome_keyboard(user_id)
            )
        else:
            # Показываем главное меню
            points_service = container.get_points_service()
            total_points = await points_service.get_total_points(user_id)
            user = await user_service.get_user(user_id)
            has_grade = user.has_grade if user else False
            grade_badge = " 🏆" if has_grade else ""

            welcome_text = f"""👋 С возвращением{", " + first_name if first_name else ""}!{grade_badge}

💎 Твои баллы: <b>{total_points}</b>

Выбери, что тебя интересует:"""

            await message.answer(welcome_text, reply_markup=get_main_keyboard())

    except TelegramAPIError as e:
        logger.error(
            f"[Common] Telegram API error in /start for user {user_id}: {e}",
            exc_info=True,
        )
        try:
            await message.answer("❌ Ошибка отправки сообщения. Попробуй позже.")
        except Exception:
            pass
    except Exception as e:
        logger.exception(f"[Common] Unexpected error in /start for user {user_id}: {e}")
        try:
            await message.answer("❌ Произошла ошибка. Попробуй позже.")
        except Exception:
            pass


@router.message(Command("home"))
async def cmd_home(message: Message, state: FSMContext):
    """Обработчик команды /home - возврат в главное меню"""
    await state.clear()
    await message.answer("🏠 Главное меню", reply_markup=get_main_keyboard())


@router.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    """Обработчик кнопки помощи"""
    help_text = """ℹ️ Помощь

📋 **Разбор ситуации:**
Опиши свою ситуацию общения или загрузи скриншот/PDF переписки. Я проанализирую и дам:
• Лучший ответ
• Прогноз реакции собеседника
• Следующие шаги
• Альтернативные стратегии

😤 **Токсичный собеседник:**
Тренируйся общаться с токсичным человеком. Сессия длится до тех пор, пока ты не переубедишь или не успокоим собеседника. В конце получишь анализ своего поведения.

🏠 Используй /home для возврата в меню"""

    await callback.message.edit_text(help_text, reply_markup=get_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "home")
async def callback_home(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await callback.message.edit_text(
        "🏠 Главное меню", reply_markup=get_main_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "module_network")
async def callback_network(callback: CallbackQuery):
    """Обработчик кнопки нетворк-чата"""
    network_link = Config.NETWORK_CHAT_LINK

    # Создаём клавиатуру со ссылкой
    builder = InlineKeyboardBuilder()
    builder.button(text="💬 Перейти в чат", url=network_link)
    builder.button(text="🏠 Домой", callback_data="home")
    builder.adjust(1)

    text = """💬 <b>Нетворк-чат</b>

Присоединяйся к нашему сообществу единомышленников! Здесь ты сможешь:
• Общаться с другими участниками
• Практиковать навыки коммуникации
• Обмениваться опытом
• Находить партнёров для тренировок"""

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "my_profile")
async def callback_my_profile(callback: CallbackQuery):
    """Профиль пользователя с баллами и статистикой"""
    from core.database import PointsConfig

    user_id = callback.from_user.id
    first_name = callback.from_user.first_name or "Пользователь"

    try:
        logger.debug(f"[Common] Profile request from user {user_id}")

        container = Container.get_instance()
        user_service = container.get_user_service()
        points_service = container.get_points_service()
        lesson_service = container.get_lesson_service()
        toxic_service = container.get_toxic_service()

        # Получаем статистику
        total_points = await points_service.get_total_points(user_id)
        points_breakdown = await points_service.get_breakdown(user_id)
        completed_lessons = await lesson_service.get_completed_count(user_id)
        total_lessons = await lesson_service.get_total_lessons_count()
        toxic_stats = await toxic_service.get_stats(user_id)
        user = await user_service.get_user(user_id)

        if not user:
            logger.warning(f"[Common] User {user_id} not found in database")
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        has_grade = user.has_grade if user else False
        onboarding_done = user.onboarding_completed if user else False

        # Формируем текст профиля
        lessons_points = points_breakdown.by_source.get("lesson", 0)
        toxic_points = points_breakdown.by_source.get("toxic_chat", 0)
        onboarding_points = points_breakdown.by_source.get("onboarding", 0)

        # Статус грейда
        if has_grade:
            grade_status = "🏆 <b>Грейд получен!</b>"
            grade_progress = "██████████ 100%"
        else:
            progress_percent = min(
                100, int(total_points / PointsConfig.GRADE_THRESHOLD * 100)
            )
            filled = progress_percent // 10
            empty = 10 - filled
            grade_progress = "█" * filled + "░" * empty + f" {progress_percent}%"
            grade_status = f"📈 До грейда: <b>{PointsConfig.GRADE_THRESHOLD - total_points}</b> баллов"

        # Бейджи
        badges = []
        if has_grade:
            badges.append("🏆")
        if completed_lessons == total_lessons and total_lessons > 0:
            badges.append("📚")
        if toxic_stats.sessions_count >= 10:
            badges.append("💪")
        if onboarding_done:
            badges.append("🎯")

        badges_text = " ".join(badges) if badges else "—"

        text = f"""👤 <b>Профиль: {first_name}</b>

💎 <b>Баллы:</b> {total_points}
{grade_progress}
{grade_status}

<b>🏅 Достижения:</b> {badges_text}

<b>📊 Источники баллов:</b>
├ 📚 Уроки: {lessons_points} ({completed_lessons}/{total_lessons})
├ 😤 Toxic Chat: {toxic_points} ({toxic_stats.sessions_count} сессий)
└ 🎯 Онбординг: {onboarding_points}

<b>📈 Статистика Toxic Chat:</b>
├ 🛡️ Границы: {toxic_stats.avg_boundaries}/10
├ 🎭 Манипуляции: {toxic_stats.avg_manipulation}/10
└ 🤝 Переговоры: {toxic_stats.avg_negotiation}/10

<b>Как заработать баллы:</b>
• Пройти урок — <b>+50</b>
• Toxic Chat — до <b>+30</b>
• Онбординг — <b>+35</b>"""

        # Клавиатура профиля
        builder = InlineKeyboardBuilder()
        builder.button(text="📚 К обучению", callback_data="module_learning")
        builder.button(text="😤 Toxic Chat", callback_data="module_toxic")
        builder.button(text="🏠 Домой", callback_data="home")
        builder.adjust(2, 1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.answer()

    except TelegramBadRequest as e:
        logger.warning(f"[Common] Cannot edit message for user {user_id}: {e}")
        try:
            await callback.message.answer(text, reply_markup=builder.as_markup())
            await callback.answer()
        except Exception:
            pass
    except TelegramAPIError as e:
        logger.error(
            f"[Common] Telegram API error in profile for user {user_id}: {e}",
            exc_info=True,
        )
        await callback.answer(
            "❌ Ошибка загрузки профиля. Попробуй позже.", show_alert=True
        )
    except Exception as e:
        logger.exception(
            f"[Common] Unexpected error in profile for user {user_id}: {e}"
        )
        await callback.answer("❌ Произошла ошибка. Попробуй позже.", show_alert=True)
