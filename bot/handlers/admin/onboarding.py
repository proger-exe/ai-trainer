"""
Обработчики админ-панели для управления вопросами онбординга
"""

import html
import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext

from core.config import Config
from core.container import Container
from bot.services.onboarding import OnboardingService
from bot.models.onboarding import OnboardingQuestionCreate, OnboardingQuestionUpdate
from bot.keyboards.admin import (
    get_admin_main_keyboard,
    get_onboarding_questions_keyboard,
    get_onboarding_question_keyboard,
    get_confirm_delete_keyboard,
    get_cancel_keyboard,
)
from bot.states.admin import AdminOnboardingQuestionStates


def is_admin(user_id: int) -> bool:
    """Проверка прав администратора"""
    return user_id in Config.ADMIN_IDS


def escape_html(text: str) -> str:
    """Экранирование HTML"""
    return html.escape(text) if text else ""


router = Router()


def get_onboarding_service() -> OnboardingService:
    """Получение OnboardingService из контейнера"""
    container = Container.get_instance()
    return container.get_onboarding_service()


# ==================== СПИСОК ВОПРОСОВ ====================


@router.callback_query(F.data == "admin_onboarding")
async def callback_admin_onboarding(callback: CallbackQuery):
    """Список вопросов онбординга"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    service = get_onboarding_service()
    questions = await service.get_all_questions(include_inactive=True)

    text = (
        "❓ <b>Управление вопросами онбординга</b>\n\nВыбери вопрос для редактирования:"
    )
    await callback.message.edit_text(
        text, reply_markup=get_onboarding_questions_keyboard(questions)
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("admin_onboarding_question_")
    & ~F.data.startswith("admin_onboarding_question_edit_")
    & ~F.data.startswith("admin_onboarding_question_delete_")
    & ~F.data.startswith("admin_onboarding_question_create")
)
async def callback_admin_onboarding_question(callback: CallbackQuery):
    """Показать вопрос"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    question_id = int(callback.data.split("_")[-1])
    service = get_onboarding_service()
    question = await service.get_question(question_id)

    if not question:
        await callback.answer("Вопрос не найден", show_alert=True)
        return

    status = "✅" if question.is_active else "❌"
    options_text = "\n".join(
        [f"{i + 1}. {opt}" for i, opt in enumerate(question.options)]
    )

    text = f"""{status} <b>Вопрос онбординга</b>

<b>Ключ:</b> {question.question_key}
<b>Заголовок:</b> {question.title}
<b>Вопрос:</b> {question.content}

<b>Варианты ответов:</b>
{options_text}

<b>Порядок:</b> {question.order}"""

    await callback.message.edit_text(
        text, reply_markup=get_onboarding_question_keyboard(question)
    )
    await callback.answer()


# ==================== СОЗДАНИЕ ВОПРОСА ====================


@router.callback_query(F.data == "admin_onboarding_question_create")
async def callback_onboarding_question_create_start(
    callback: CallbackQuery, state: FSMContext
):
    """Начало создания вопроса"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    await state.set_state(AdminOnboardingQuestionStates.waiting_for_key)
    await callback.message.edit_text(
        "❓ <b>Создание вопроса онбординга</b>\n\nВведи уникальный ключ вопроса (например: main_challenge):",
        reply_markup=get_cancel_keyboard("admin_onboarding"),
    )
    await callback.answer()


@router.message(StateFilter(AdminOnboardingQuestionStates.waiting_for_key))
async def process_onboarding_question_key(message: Message, state: FSMContext):
    """Обработка ключа вопроса"""
    question_key = message.text.strip()

    service = get_onboarding_service()
    existing = await service.get_question_by_key(question_key)
    if existing:
        await message.answer(
            "❌ Вопрос с таким ключом уже существует. Введи другой ключ:"
        )
        return

    await state.update_data(question_key=question_key)
    await state.set_state(AdminOnboardingQuestionStates.waiting_for_title)
    await message.answer("Введи заголовок вопроса (например: Вопрос 1 из 5 🎯):")


@router.message(StateFilter(AdminOnboardingQuestionStates.waiting_for_title))
async def process_onboarding_question_title(message: Message, state: FSMContext):
    """Обработка заголовка вопроса"""
    title = message.text.strip()
    await state.update_data(title=title)
    await state.set_state(AdminOnboardingQuestionStates.waiting_for_content)
    await message.answer("Введи текст вопроса:")


@router.message(StateFilter(AdminOnboardingQuestionStates.waiting_for_content))
async def process_onboarding_question_content(message: Message, state: FSMContext):
    """Обработка текста вопроса"""
    content = message.text.strip()
    await state.update_data(content=content)
    await state.set_state(AdminOnboardingQuestionStates.waiting_for_options)
    await message.answer(
        "Введи варианты ответов, каждый с новой строки (минимум 2 варианта):"
    )


@router.message(StateFilter(AdminOnboardingQuestionStates.waiting_for_options))
async def process_onboarding_question_options(message: Message, state: FSMContext):
    """Обработка вариантов ответов"""
    options_text = message.text.strip()
    options = [opt.strip() for opt in options_text.split("\n") if opt.strip()]

    if len(options) < 2:
        await message.answer(
            "❌ Нужно минимум 2 варианта ответа. Введи варианты снова:"
        )
        return

    data = await state.get_data()
    await state.set_state(AdminOnboardingQuestionStates.waiting_for_order)
    await state.update_data(options=options)

    service = get_onboarding_service()
    all_questions = await service.get_all_questions(include_inactive=True)
    max_order = max([q.order for q in all_questions], default=-1)

    await message.answer(
        f"Введи порядок отображения (по умолчанию будет {max_order + 1}):"
    )


@router.message(StateFilter(AdminOnboardingQuestionStates.waiting_for_order))
async def process_onboarding_question_order(message: Message, state: FSMContext):
    """Обработка порядка и создание вопроса"""
    try:
        order = int(message.text.strip()) if message.text.strip() else 0
    except ValueError:
        order = 0

    data = await state.get_data()

    service = get_onboarding_service()
    question = await service.create_question(
        OnboardingQuestionCreate(
            question_key=data["question_key"],
            title=data["title"],
            content=data["content"],
            options=data["options"],
            order=order,
            is_active=True,
        )
    )

    await state.clear()
    await message.answer(
        f"✅ Вопрос создан!\n\nКлюч: {question.question_key}\nЗаголовок: {question.title}"
    )

    # Показываем список вопросов
    questions = await service.get_all_questions(include_inactive=True)
    await message.answer(
        "❓ <b>Управление вопросами онбординга</b>\n\nВыбери вопрос для редактирования:",
        reply_markup=get_onboarding_questions_keyboard(questions),
    )


# ==================== РЕДАКТИРОВАНИЕ ВОПРОСА ====================


@router.callback_query(F.data.startswith("admin_onboarding_question_edit_"))
async def callback_onboarding_question_edit_start(
    callback: CallbackQuery, state: FSMContext
):
    """Начало редактирования вопроса"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    question_id = int(callback.data.split("_")[-1])
    service = get_onboarding_service()
    question = await service.get_question(question_id)

    if not question:
        await callback.answer("Вопрос не найден", show_alert=True)
        return

    await state.update_data(question_id=question_id, current_question=question)
    await state.set_state(AdminOnboardingQuestionStates.waiting_for_edit_field)

    text = f"""✏️ <b>Редактирование вопроса</b>

Что хочешь изменить?
1. Заголовок
2. Текст вопроса
3. Варианты ответов (введи номера через запятую, например: 1,2,3)
4. Порядок
5. Статус (активен/неактивен)

Введи номер или отправь /cancel для отмены:"""

    await callback.message.edit_text(
        text,
        reply_markup=get_cancel_keyboard(f"admin_onboarding_question_{question_id}"),
    )
    await callback.answer()


@router.message(StateFilter(AdminOnboardingQuestionStates.waiting_for_edit_field))
async def process_onboarding_question_edit_field(message: Message, state: FSMContext):
    """Обработка выбора поля для редактирования"""
    choice = message.text.strip()
    data = await state.get_data()
    question = data["current_question"]

    if choice == "1":
        await state.set_state(AdminOnboardingQuestionStates.waiting_for_edit_title)
        await message.answer(
            f"Текущий заголовок: {question.title}\n\nВведи новый заголовок:"
        )
    elif choice == "2":
        await state.set_state(AdminOnboardingQuestionStates.waiting_for_edit_content)
        await message.answer(
            f"Текущий текст: {question.content}\n\nВведи новый текст вопроса:"
        )
    elif choice == "3":
        await state.set_state(AdminOnboardingQuestionStates.waiting_for_edit_options)
        options_text = "\n".join(
            [f"{i + 1}. {opt}" for i, opt in enumerate(question.options)]
        )
        await message.answer(
            f"Текущие варианты:\n{options_text}\n\nВведи новые варианты, каждый с новой строки:"
        )
    elif choice == "4":
        await state.set_state(AdminOnboardingQuestionStates.waiting_for_edit_order)
        await message.answer(
            f"Текущий порядок: {question.order}\n\nВведи новый порядок:"
        )
    elif choice == "5":
        # Переключение статуса
        service = get_onboarding_service()
        new_status = not question.is_active
        await service.update_question(
            question.id, OnboardingQuestionUpdate(is_active=new_status)
        )
        await state.clear()
        status_text = "активирован" if new_status else "деактивирован"
        await message.answer(f"✅ Вопрос {status_text}!")

        # Показываем обновленный вопрос
        updated_question = await service.get_question(question.id)
        if updated_question:
            status = "✅" if updated_question.is_active else "❌"
            options_text = "\n".join(
                [f"{i + 1}. {opt}" for i, opt in enumerate(updated_question.options)]
            )
            text = f"""{status} <b>Вопрос онбординга</b>

<b>Ключ:</b> {updated_question.question_key}
<b>Заголовок:</b> {updated_question.title}
<b>Вопрос:</b> {updated_question.content}

<b>Варианты ответов:</b>
{options_text}

<b>Порядок:</b> {updated_question.order}"""
            await message.answer(
                text, reply_markup=get_onboarding_question_keyboard(updated_question)
            )
        return
    else:
        await message.answer("❌ Неверный выбор. Введи число от 1 до 5:")


@router.message(StateFilter(AdminOnboardingQuestionStates.waiting_for_edit_title))
async def process_onboarding_question_edit_title(message: Message, state: FSMContext):
    """Обработка нового заголовка"""
    new_title = message.text.strip()
    data = await state.get_data()

    service = get_onboarding_service()
    await service.update_question(
        data["question_id"], OnboardingQuestionUpdate(title=new_title)
    )

    await state.clear()
    await message.answer("✅ Заголовок обновлен!")

    # Показываем обновленный вопрос
    updated_question = await service.get_question(data["question_id"])
    if updated_question:
        status = "✅" if updated_question.is_active else "❌"
        options_text = "\n".join(
            [f"{i + 1}. {opt}" for i, opt in enumerate(updated_question.options)]
        )
        text = f"""{status} <b>Вопрос онбординга</b>

<b>Ключ:</b> {updated_question.question_key}
<b>Заголовок:</b> {updated_question.title}
<b>Вопрос:</b> {updated_question.content}

<b>Варианты ответов:</b>
{options_text}

<b>Порядок:</b> {updated_question.order}"""
        await message.answer(
            text, reply_markup=get_onboarding_question_keyboard(updated_question)
        )


@router.message(StateFilter(AdminOnboardingQuestionStates.waiting_for_edit_content))
async def process_onboarding_question_edit_content(message: Message, state: FSMContext):
    """Обработка нового текста вопроса"""
    new_content = message.text.strip()
    data = await state.get_data()

    service = get_onboarding_service()
    await service.update_question(
        data["question_id"], OnboardingQuestionUpdate(content=new_content)
    )

    await state.clear()
    await message.answer("✅ Текст вопроса обновлен!")

    # Показываем обновленный вопрос
    updated_question = await service.get_question(data["question_id"])
    if updated_question:
        status = "✅" if updated_question.is_active else "❌"
        options_text = "\n".join(
            [f"{i + 1}. {opt}" for i, opt in enumerate(updated_question.options)]
        )
        text = f"""{status} <b>Вопрос онбординга</b>

<b>Ключ:</b> {updated_question.question_key}
<b>Заголовок:</b> {updated_question.title}
<b>Вопрос:</b> {updated_question.content}

<b>Варианты ответов:</b>
{options_text}

<b>Порядок:</b> {updated_question.order}"""
        await message.answer(
            text, reply_markup=get_onboarding_question_keyboard(updated_question)
        )


@router.message(StateFilter(AdminOnboardingQuestionStates.waiting_for_edit_options))
async def process_onboarding_question_edit_options(message: Message, state: FSMContext):
    """Обработка новых вариантов ответов"""
    options_text = message.text.strip()
    options = [opt.strip() for opt in options_text.split("\n") if opt.strip()]

    if len(options) < 2:
        await message.answer(
            "❌ Нужно минимум 2 варианта ответа. Введи варианты снова:"
        )
        return

    data = await state.get_data()

    service = get_onboarding_service()
    await service.update_question(
        data["question_id"], OnboardingQuestionUpdate(options=options)
    )

    await state.clear()
    await message.answer("✅ Варианты ответов обновлены!")

    # Показываем обновленный вопрос
    updated_question = await service.get_question(data["question_id"])
    if updated_question:
        status = "✅" if updated_question.is_active else "❌"
        options_text = "\n".join(
            [f"{i + 1}. {opt}" for i, opt in enumerate(updated_question.options)]
        )
        text = f"""{status} <b>Вопрос онбординга</b>

<b>Ключ:</b> {updated_question.question_key}
<b>Заголовок:</b> {updated_question.title}
<b>Вопрос:</b> {updated_question.content}

<b>Варианты ответов:</b>
{options_text}

<b>Порядок:</b> {updated_question.order}"""
        await message.answer(
            text, reply_markup=get_onboarding_question_keyboard(updated_question)
        )


@router.message(StateFilter(AdminOnboardingQuestionStates.waiting_for_edit_order))
async def process_onboarding_question_edit_order(message: Message, state: FSMContext):
    """Обработка нового порядка"""
    try:
        new_order = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи число:")
        return

    data = await state.get_data()

    service = get_onboarding_service()
    await service.update_question(
        data["question_id"], OnboardingQuestionUpdate(order=new_order)
    )

    await state.clear()
    await message.answer("✅ Порядок обновлен!")

    # Показываем обновленный вопрос
    updated_question = await service.get_question(data["question_id"])
    if updated_question:
        status = "✅" if updated_question.is_active else "❌"
        options_text = "\n".join(
            [f"{i + 1}. {opt}" for i, opt in enumerate(updated_question.options)]
        )
        text = f"""{status} <b>Вопрос онбординга</b>

<b>Ключ:</b> {updated_question.question_key}
<b>Заголовок:</b> {updated_question.title}
<b>Вопрос:</b> {updated_question.content}

<b>Варианты ответов:</b>
{options_text}

<b>Порядок:</b> {updated_question.order}"""
        await message.answer(
            text, reply_markup=get_onboarding_question_keyboard(updated_question)
        )


# ==================== УДАЛЕНИЕ ВОПРОСА ====================


@router.callback_query(
    F.data.startswith("admin_onboarding_question_delete_")
    & ~F.data.endswith("_confirm")
)
async def callback_onboarding_question_delete(callback: CallbackQuery):
    """Подтверждение удаления вопроса"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    question_id = int(callback.data.split("_")[-1])
    service = get_onboarding_service()
    question = await service.get_question(question_id)

    if not question:
        await callback.answer("Вопрос не найден", show_alert=True)
        return

    text = f"⚠️ <b>Удаление вопроса</b>\n\nТы уверен, что хочешь удалить вопрос:\n\n<b>{question.title}</b>\n\n{question.content}"
    await callback.message.edit_text(
        text,
        reply_markup=get_confirm_delete_keyboard(
            "onboarding_question",
            question_id,
            f"admin_onboarding_question_{question_id}",
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_onboarding_question_delete_confirm_"))
async def callback_onboarding_question_delete_confirm(callback: CallbackQuery):
    """Удаление вопроса"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    question_id = int(callback.data.split("_")[-1])
    service = get_onboarding_service()

    success = await service.delete_question(question_id)
    if success:
        await callback.answer("✅ Вопрос удален!", show_alert=True)

        # Показываем список вопросов
        questions = await service.get_all_questions(include_inactive=True)
        await callback.message.edit_text(
            "❓ <b>Управление вопросами онбординга</b>\n\nВыбери вопрос для редактирования:",
            reply_markup=get_onboarding_questions_keyboard(questions),
        )
    else:
        await callback.answer("❌ Ошибка при удалении", show_alert=True)
    await callback.answer()


# ==================== ОТМЕНА ====================


@router.message(Command("cancel"), StateFilter(AdminOnboardingQuestionStates))
async def cancel_onboarding_question_edit(message: Message, state: FSMContext):
    """Отмена редактирования вопроса"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У тебя нет доступа")
        return

    await state.clear()
    service = get_onboarding_service()
    questions = await service.get_all_questions(include_inactive=True)
    await message.answer(
        "❌ Редактирование отменено.\n\n❓ <b>Управление вопросами онбординга</b>\n\nВыбери вопрос для редактирования:",
        reply_markup=get_onboarding_questions_keyboard(questions),
    )
