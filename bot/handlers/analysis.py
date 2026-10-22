"""
Обработчики для модуля разбора ситуаций
"""

import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from core.container import Container
from core.bridge import bridge
from bot.states import AnalysisStates
from bot.keyboards import (
    get_analysis_keyboard,
    get_continue_keyboard,
    get_home_keyboard,
)

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "module_analysis")
async def callback_analysis_start(callback: CallbackQuery, state: FSMContext):
    """Начало модуля разбора ситуаций"""
    await state.set_state(AnalysisStates.waiting_for_situation)

    text = """📋 <b>Разбор ситуации</b>

Опиши свою ситуацию общения или загрузи файл (скриншот/PDF).

Ты можешь:
• Написать текст ситуации
• Загрузить скриншот переписки
• Загрузить PDF файл

После анализа ты сможешь продолжить разбор вопросами типа 'а что если он скажет ___?'"""

    await callback.message.edit_text(text, reply_markup=get_analysis_keyboard())
    await callback.answer()


@router.callback_query(F.data == "set_goal")
async def callback_set_goal(callback: CallbackQuery, state: FSMContext):
    """Установка цели общения"""
    await state.set_state(AnalysisStates.waiting_for_goal)

    text = "🎯 Укажи цель общения (например: 'договориться о встрече', 'успокоить конфликт', 'получить согласие'). Или отправь /skip чтобы пропустить."

    await callback.message.edit_text(text)
    await callback.answer()


@router.message(StateFilter(AnalysisStates.waiting_for_goal))
async def process_goal(message: Message, state: FSMContext):
    """Обработка цели общения"""
    goal = message.text
    user_id = message.from_user.id

    # Сохраняем цель
    container = Container.get_instance()
    db = container.get_db()
    context = await db.get_analysis_context(user_id)
    await db.save_analysis_context(
        user_id, context.get("context_data", {}) if context else {}, goal
    )

    await state.set_state(AnalysisStates.waiting_for_situation)
    await message.answer(
        f"✅ Цель общения сохранена: {goal}\n\nТеперь опиши ситуацию или загрузи файл."
    )


@router.message(Command("skip"))
async def cmd_skip(message: Message, state: FSMContext):
    """Пропуск установки цели"""
    if await state.get_state() == AnalysisStates.waiting_for_goal:
        await state.set_state(AnalysisStates.waiting_for_situation)
        await message.answer(
            "Окей, цель не указана. Теперь опиши ситуацию или загрузи файл."
        )


@router.message(StateFilter(AnalysisStates.waiting_for_situation), F.text)
async def process_situation_text(message: Message, state: FSMContext):
    """Обработка текстовой ситуации"""
    from bot.utils.validation import validate_user_id
    from aiogram.exceptions import TelegramAPIError

    try:
        user_id = validate_user_id(message.from_user.id)
        situation_text = message.text

        if not situation_text or not situation_text.strip():
            await message.answer("❌ Введи описание ситуации.")
            return

        logger.debug(f"[Analysis] Processing situation text from user {user_id}")

        # Проверяем, есть ли уже история - если да, то это продолжение, а не новая ситуация
        container = Container.get_instance()
        db = container.get_db()
        context = await db.get_analysis_context(user_id) or {}
        context_data = context.get("context_data", {}) if context else {}
        history = context_data.get("history", [])

        if history:
            # Если есть история, обрабатываем как продолжение
            await state.set_state(AnalysisStates.waiting_for_continue)
            await process_continue_question(message, state)
            return

        # Новая ситуация
        # Сохраняем message_id филлер-сообщения для последующего редактирования
        loading_msg = await message.answer("⏳ Анализирую ситуацию...")
        loading_msg_id = loading_msg.message_id

        # Сохраняем message_id в контексте для редактирования
        context_data["loading_msg_id"] = loading_msg_id
        context_data["loading_chat_id"] = message.chat.id
        await db.save_analysis_context(user_id, context_data, context.get("goal"))

        # Отправляем команду в модель ANALYSIS через bridge
        command = f"ANALYZE {user_id}&&{situation_text} => ANALYSIS"
        bridge.send_to_atlant(command)

        # Автоматически переводим в состояние продолжения
        await state.set_state(AnalysisStates.waiting_for_continue)

    except TelegramAPIError as e:
        logger.error(
            f"[Analysis] Telegram API error in process_situation_text for user {user_id}: {e}",
            exc_info=True,
        )
        try:
            await message.answer("❌ Ошибка отправки сообщения. Попробуй позже.")
        except Exception:
            pass
    except Exception as e:
        logger.exception(
            f"[Analysis] Unexpected error in process_situation_text for user {user_id}: {e}"
        )
        try:
            await message.answer("❌ Произошла ошибка. Попробуй позже.")
        except Exception:
            pass


@router.message(StateFilter(AnalysisStates.waiting_for_situation), F.photo | F.document)
async def process_situation_file(message: Message, state: FSMContext):
    """Обработка файла (скриншот/PDF)"""
    if message.photo:
        await message.answer(
            "📸 Я вижу скриншот. Пожалуйста, опиши ситуацию текстом или задай вопрос по скриншоту."
        )
        await state.set_state(AnalysisStates.waiting_for_situation)

    elif message.document:
        mime_type = message.document.mime_type
        if mime_type == "application/pdf":
            await message.answer(
                "📄 Я вижу PDF файл. Пожалуйста, опиши ситуацию текстом или задай вопрос по документу."
            )
            await state.set_state(AnalysisStates.waiting_for_situation)
        else:
            await message.answer("❌ Поддерживаются только PDF файлы и изображения.")


@router.callback_query(F.data == "end_analysis")
async def callback_end_analysis(callback: CallbackQuery, state: FSMContext):
    """Завершение разбора ситуации"""
    user_id = callback.from_user.id

    # Очищаем контекст
    container = Container.get_instance()
    db = container.get_db()
    await db.clear_analysis_context(user_id)

    # Возвращаем в главное меню
    await state.clear()
    await callback.message.answer(
        "✅ Разбор завершён. Возвращаю в главное меню.",
        reply_markup=get_home_keyboard(),
    )
    await callback.answer()


@router.message(StateFilter(AnalysisStates.waiting_for_continue))
async def process_continue_question(message: Message, state: FSMContext):
    """Обработка продолжения разбора"""
    user_id = message.from_user.id
    question_text = message.text

    # Сохраняем message_id филлер-сообщения для последующего редактирования
    loading_msg = await message.answer("⏳ Анализирую...")
    loading_msg_id = loading_msg.message_id

    # Сохраняем message_id в контексте для редактирования
    container = Container.get_instance()
    db = container.get_db()
    context = await db.get_analysis_context(user_id) or {}
    context_data = context.get("context_data", {}) if context else {}
    context_data["loading_msg_id"] = loading_msg_id
    context_data["loading_chat_id"] = message.chat.id
    await db.save_analysis_context(user_id, context_data, context.get("goal"))

    # Отправляем команду в модель ANALYSIS через bridge
    command = f"CONTINUE {user_id}&&{question_text} => ANALYSIS"
    bridge.send_to_atlant(command)
