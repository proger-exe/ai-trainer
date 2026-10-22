"""
Обработчики для модуля токсичного собеседника
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest

from core.container import Container
from core.bridge import bridge
from bot.states import ToxicStates
from bot.keyboards import get_toxic_keyboard, get_home_keyboard
from bot.utils.validation import validate_user_id

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "module_toxic")
async def callback_toxic_start(callback: CallbackQuery, state: FSMContext):
    """Начало модуля токсичного собеседника"""
    try:
        user_id = validate_user_id(callback.from_user.id)
        logger.debug(f"[Toxic] Starting module for user {user_id}")

        # Проверяем, есть ли активная сессия
        container = Container.get_instance()
        db = container.get_db()
        context = await db.get_toxic_context(user_id)
        if context and context.get("history"):
            # Продолжаем существующую сессию
            await state.set_state(ToxicStates.in_session)
            text = "😤 Продолжаем сессию с токсичным собеседником. Напиши сообщение:"
            await callback.message.edit_text(text, reply_markup=get_toxic_keyboard())
        else:
            # Начинаем новую сессию - запускаем модель для первого сообщения
            await state.set_state(ToxicStates.in_session)
            text = """😤 <b>Токсичный собеседник</b>

Ты будешь общаться с токсичным собеседником. Твоя задача — переубедить или успокоить его.

Сессия закончится, когда ты справишься с задачей. В конце получишь анализ своего поведения.

Токсичный собеседник начинает диалог..."""
            await callback.message.edit_text(text, reply_markup=get_toxic_keyboard())

            # Запускаем модель для первого сообщения
            command = f"START_TOXIC {user_id} => TOXIC"
            bridge.send_to_atlant(command)

        await callback.answer()

    except TelegramBadRequest as e:
        logger.warning(f"[Toxic] Cannot edit message for user {user_id}: {e}")
        try:
            await callback.message.answer(text, reply_markup=get_toxic_keyboard())
            await callback.answer()
        except Exception:
            pass
    except TelegramAPIError as e:
        logger.error(
            f"[Toxic] Telegram API error starting module for user {user_id}: {e}",
            exc_info=True,
        )
        await callback.answer(
            "❌ Ошибка запуска модуля. Попробуй позже.", show_alert=True
        )
    except Exception as e:
        logger.exception(
            f"[Toxic] Unexpected error starting module for user {user_id}: {e}"
        )
        await callback.answer("❌ Произошла ошибка. Попробуй позже.", show_alert=True)


@router.message(StateFilter(ToxicStates.in_session), F.text)
async def process_toxic_message(message: Message, state: FSMContext):
    """Обработка сообщения в сессии токсичного собеседника"""
    try:
        user_id = validate_user_id(message.from_user.id)
        user_message = message.text

        if not user_message or not user_message.strip():
            await message.answer("❌ Сообщение не может быть пустым.")
            return

        logger.debug(f"[Toxic] Processing message from user {user_id}")

        # Сохраняем message_id для последующего редактирования
        loading_msg = await message.answer("⏳ Токсичный собеседник печатает...")
        loading_msg_id = loading_msg.message_id

        # Сохраняем message_id в контексте для редактирования
        container = Container.get_instance()
        db = container.get_db()
        context = await db.get_toxic_context(user_id) or {}
        context["loading_msg_id"] = loading_msg_id
        context["loading_chat_id"] = message.chat.id
        await db.save_toxic_context(user_id, context, session_active=True)

        # Отправляем команду в модель TOXIC через bridge
        command = f"TOXIC_MESSAGE {user_id}&&{user_message} => TOXIC"
        bridge.send_to_atlant(command)

    except TelegramAPIError as e:
        logger.error(
            f"[Toxic] Telegram API error in process_toxic_message for user {user_id}: {e}",
            exc_info=True,
        )
        try:
            await message.answer("❌ Ошибка отправки сообщения. Попробуй позже.")
        except Exception:
            pass
    except Exception as e:
        logger.exception(
            f"[Toxic] Unexpected error in process_toxic_message for user {user_id}: {e}"
        )
        try:
            await message.answer("❌ Произошла ошибка. Попробуй позже.")
        except Exception:
            pass


@router.callback_query(F.data == "end_toxic")
async def callback_end_toxic(callback: CallbackQuery, state: FSMContext):
    """Завершение сессии токсичного собеседника"""
    try:
        user_id = validate_user_id(callback.from_user.id)
        logger.info(f"[Toxic] Ending session for user {user_id}")

        # Сохраняем message_id для редактирования
        loading_msg_id = callback.message.message_id
        loading_chat_id = callback.message.chat.id

        # Сохраняем в контексте
        container = Container.get_instance()
        db = container.get_db()
        context = await db.get_toxic_context(user_id) or {}
        context["analysis_loading_msg_id"] = loading_msg_id
        context["analysis_loading_chat_id"] = loading_chat_id
        await db.save_toxic_context(user_id, context, session_active=True)

        # Редактируем сообщение
        await callback.message.edit_text("⏳ Анализирую твоё поведение...")

        # Отправляем команду на завершение сессии через bridge
        command = f"END_TOXIC {user_id} => TOXIC"
        bridge.send_to_atlant(command)

        await state.clear()
        await callback.answer()

    except TelegramBadRequest as e:
        logger.warning(f"[Toxic] Cannot edit message for user {user_id}: {e}")
        try:
            await callback.message.answer("⏳ Анализирую твоё поведение...")
            await callback.answer()
        except Exception:
            pass
    except TelegramAPIError as e:
        logger.error(
            f"[Toxic] Telegram API error ending session for user {user_id}: {e}",
            exc_info=True,
        )
        await callback.answer(
            "❌ Ошибка завершения сессии. Попробуй позже.", show_alert=True
        )
    except Exception as e:
        logger.exception(
            f"[Toxic] Unexpected error ending session for user {user_id}: {e}"
        )
        await callback.answer("❌ Произошла ошибка. Попробуй позже.", show_alert=True)
