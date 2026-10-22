"""
Обработчики админ-панели для управления уроками
"""

import html
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from core.config import Config
from core.container import Container
from bot.services.lesson import LessonService
from bot.models.lesson import (
    BlockCreate,
    BlockUpdate,
    LessonCreate,
    LessonUpdate,
    FragmentCreate,
    FragmentUpdate,
    FragmentType,
)
from bot.keyboards.admin import (
    get_admin_main_keyboard,
    get_blocks_admin_keyboard,
    get_lessons_admin_keyboard,
    get_fragments_admin_keyboard,
    get_fragment_admin_keyboard,
    get_confirm_delete_keyboard,
    get_cancel_keyboard,
    get_fragment_type_keyboard,
)
from bot.states.admin import AdminBlockStates, AdminLessonStates, AdminFragmentStates


def is_admin(user_id: int) -> bool:
    """Проверка прав администратора"""
    return user_id in Config.ADMIN_IDS


def escape_html(text: str) -> str:
    """Экранирование HTML"""
    return html.escape(text) if text else ""


router = Router()


def get_lesson_service() -> LessonService:
    """Получение LessonService из контейнера"""
    container = Container.get_instance()
    return container.get_lesson_service()


# ==================== БЛОКИ ====================


@router.callback_query(F.data == "admin_lessons")
async def callback_admin_lessons(callback: CallbackQuery):
    """Список блоков"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    service = get_lesson_service()
    blocks = await service.get_all_blocks(include_inactive=True)

    # Загружаем уроки для каждого блока
    for block in blocks:
        block.lessons = await service.get_lessons_by_block(block.id)

    text = "📚 <b>Управление уроками</b>\n\nВыбери блок для редактирования:"
    await callback.message.edit_text(
        text, reply_markup=get_blocks_admin_keyboard(blocks)
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("admin_block_")
    & ~F.data.startswith("admin_block_edit_")
    & ~F.data.startswith("admin_block_delete_")
    & ~F.data.startswith("admin_block_create")
)
async def callback_admin_block(callback: CallbackQuery):
    """Показать блок с уроками"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    block_id = int(callback.data.split("_")[-1])
    service = get_lesson_service()
    block = await service.get_block(block_id, include_lessons=True)

    if not block:
        await callback.answer("Блок не найден", show_alert=True)
        return

    text = f"""{block.emoji} <b>{block.title}</b>

{block.description or "Без описания"}

<b>Уроки блока:</b>"""

    await callback.message.edit_text(
        text, reply_markup=get_lessons_admin_keyboard(block)
    )
    await callback.answer()


@router.callback_query(F.data == "admin_block_create")
async def callback_block_create_start(callback: CallbackQuery, state: FSMContext):
    """Начало создания блока"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    await state.set_state(AdminBlockStates.waiting_for_title)
    await callback.message.edit_text(
        "📝 <b>Создание блока</b>\n\nВведи название блока:",
        reply_markup=get_cancel_keyboard("admin_lessons"),
    )
    await callback.answer()


@router.message(StateFilter(AdminBlockStates.waiting_for_title))
async def process_block_title(message: Message, state: FSMContext):
    """Обработка названия блока"""
    await state.update_data(title=message.text)
    await state.set_state(AdminBlockStates.waiting_for_emoji)
    await message.answer(
        "Введи эмодзи для блока (например: 🛡️):",
        reply_markup=get_cancel_keyboard("admin_lessons"),
    )


@router.message(StateFilter(AdminBlockStates.waiting_for_emoji))
async def process_block_emoji(message: Message, state: FSMContext):
    """Обработка эмодзи блока"""
    await state.update_data(emoji=message.text)
    await state.set_state(AdminBlockStates.waiting_for_description)
    await message.answer(
        "Введи описание блока (или /skip чтобы пропустить):",
        reply_markup=get_cancel_keyboard("admin_lessons"),
    )


@router.message(StateFilter(AdminBlockStates.waiting_for_description))
async def process_block_description(message: Message, state: FSMContext):
    """Обработка описания блока"""
    description = None if message.text == "/skip" else message.text
    await state.update_data(description=description)
    await state.set_state(AdminBlockStates.waiting_for_order)
    await message.answer(
        "Введи порядковый номер блока (число):",
        reply_markup=get_cancel_keyboard("admin_lessons"),
    )


@router.message(StateFilter(AdminBlockStates.waiting_for_order))
async def process_block_order(message: Message, state: FSMContext):
    """Обработка порядка блока и создание"""
    try:
        order = int(message.text)
        data = await state.get_data()

        service = get_lesson_service()
        block = await service.create_block(
            BlockCreate(
                title=data["title"],
                emoji=data["emoji"],
                description=data.get("description"),
                order=order,
            )
        )

        await state.clear()
        await message.answer(
            f"✅ Блок '{block.title}' создан!", reply_markup=get_admin_main_keyboard()
        )
    except ValueError:
        await message.answer(
            "❌ Неверный формат числа. Попробуй ещё раз:",
            reply_markup=get_cancel_keyboard("admin_lessons"),
        )


@router.callback_query(F.data.startswith("admin_block_edit_"))
async def callback_block_edit(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования блока"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    block_id = int(callback.data.split("_")[-1])
    service = get_lesson_service()
    block = await service.get_block(block_id)

    if not block:
        await callback.answer("Блок не найден", show_alert=True)
        return

    await state.update_data(block_id=block_id)
    await state.set_state(AdminBlockStates.waiting_for_title)
    await callback.message.edit_text(
        f"✏️ <b>Редактирование блока</b>\n\nТекущее название: {block.title}\nВведи новое название (или /skip):",
        reply_markup=get_cancel_keyboard(f"admin_block_{block_id}"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_block_delete_"))
async def callback_block_delete(callback: CallbackQuery):
    """Подтверждение удаления блока"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    block_id = int(callback.data.split("_")[-1])
    service = get_lesson_service()
    block = await service.get_block(block_id)

    if not block:
        await callback.answer("Блок не найден", show_alert=True)
        return

    text = f"⚠️ <b>Удаление блока</b>\n\nТы уверен, что хочешь удалить блок '{block.title}'?\n\nВсе уроки и фрагменты в блоке также будут удалены!"
    await callback.message.edit_text(
        text,
        reply_markup=get_confirm_delete_keyboard(
            "block", block_id, f"admin_block_{block_id}"
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_block_delete_confirm_"))
async def callback_block_delete_confirm(callback: CallbackQuery):
    """Подтверждённое удаление блока"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    block_id = int(callback.data.split("_")[-1])
    service = get_lesson_service()

    success = await service.delete_block(block_id)
    if success:
        await callback.message.edit_text(
            "✅ Блок удалён", reply_markup=get_admin_main_keyboard()
        )
    else:
        await callback.answer("Ошибка при удалении", show_alert=True)
    await callback.answer()


# ==================== УРОКИ ====================


@router.callback_query(
    F.data.startswith("admin_lesson_")
    & ~F.data.startswith("admin_lesson_edit_")
    & ~F.data.startswith("admin_lesson_delete_")
    & ~F.data.startswith("admin_lesson_create_")
)
async def callback_admin_lesson(callback: CallbackQuery):
    """Показать урок с фрагментами"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    lesson_id = int(callback.data.split("_")[-1])
    service = get_lesson_service()
    lesson = await service.get_lesson(lesson_id, include_fragments=True)

    if not lesson:
        await callback.answer("Урок не найден", show_alert=True)
        return

    fragments_count = len(lesson.fragments) if lesson.fragments else 0
    safe_title = escape_html(lesson.title)

    text = f"""📖 <b>Урок: {safe_title}</b>

<b>Порядок:</b> {lesson.order}
<b>Статус:</b> {"✅ Активен" if lesson.is_active else "❌ Неактивен"}
<b>Фрагментов:</b> {fragments_count}"""

    await callback.message.edit_text(
        text, reply_markup=get_fragments_admin_keyboard(lesson)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_lesson_create_"))
async def callback_lesson_create_start(callback: CallbackQuery, state: FSMContext):
    """Начало создания урока"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    block_id = int(callback.data.split("_")[-1])
    await state.update_data(block_id=block_id)
    await state.set_state(AdminLessonStates.waiting_for_title)
    await callback.message.edit_text(
        "📝 <b>Создание урока</b>\n\nВведи название урока:",
        reply_markup=get_cancel_keyboard(f"admin_block_{block_id}"),
    )
    await callback.answer()


@router.message(StateFilter(AdminLessonStates.waiting_for_title))
async def process_lesson_title(message: Message, state: FSMContext):
    """Обработка названия урока"""
    data = await state.get_data()
    editing_lesson_id = data.get("editing_lesson_id")

    if message.text == "/skip" and editing_lesson_id:
        service = get_lesson_service()
        lesson = await service.get_lesson(editing_lesson_id)
        if lesson:
            await state.update_data(title=lesson.title)
    else:
        await state.update_data(title=message.text)

    await state.set_state(AdminLessonStates.waiting_for_order)

    if editing_lesson_id:
        service = get_lesson_service()
        lesson = await service.get_lesson(editing_lesson_id)
        current_order = lesson.order if lesson else 1
        await message.answer(
            f"Текущий порядок: {current_order}\n\nВведи новый порядковый номер (или /skip):",
            reply_markup=get_cancel_keyboard(f"admin_lesson_{editing_lesson_id}"),
        )
    else:
        await message.answer(
            "Введи порядковый номер урока в блоке (число):",
            reply_markup=get_cancel_keyboard(),
        )


@router.message(StateFilter(AdminLessonStates.waiting_for_order))
async def process_lesson_order(message: Message, state: FSMContext):
    """Обработка порядка урока и создание/обновление"""
    data = await state.get_data()
    editing_lesson_id = data.get("editing_lesson_id")
    service = get_lesson_service()

    if message.text == "/skip" and editing_lesson_id:
        lesson = await service.get_lesson(editing_lesson_id)
        order = lesson.order if lesson else 1
    else:
        try:
            order = int(message.text)
        except ValueError:
            await message.answer(
                "❌ Неверный формат числа. Попробуй ещё раз:",
                reply_markup=get_cancel_keyboard(),
            )
            return

    if editing_lesson_id:
        updated = await service.update_lesson(
            editing_lesson_id, LessonUpdate(title=data["title"], order=order)
        )
        await state.clear()

        if updated:
            await message.answer(
                f"✅ Урок '<b>{escape_html(updated.title)}</b>' обновлён!",
                reply_markup=get_fragments_admin_keyboard(updated),
            )
        else:
            await message.answer(
                "❌ Ошибка при обновлении урока", reply_markup=get_admin_main_keyboard()
            )
    else:
        lesson = await service.create_lesson(
            LessonCreate(block_id=data["block_id"], title=data["title"], order=order)
        )

        await state.clear()
        block = await service.get_block(data["block_id"])
        await message.answer(
            f"✅ Урок '<b>{escape_html(lesson.title)}</b>' создан!",
            reply_markup=(
                get_fragments_admin_keyboard(lesson)
                if lesson
                else get_admin_main_keyboard()
            ),
        )


@router.callback_query(F.data.startswith("admin_lesson_edit_"))
async def callback_lesson_edit_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования урока"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    lesson_id = int(callback.data.split("_")[-1])
    service = get_lesson_service()
    lesson = await service.get_lesson(lesson_id)

    if not lesson:
        await callback.answer("Урок не найден", show_alert=True)
        return

    await state.update_data(editing_lesson_id=lesson_id, block_id=lesson.block_id)
    await state.set_state(AdminLessonStates.waiting_for_title)
    safe_title = escape_html(lesson.title)
    await callback.message.edit_text(
        f"✏️ <b>Редактирование урока</b>\n\n"
        f"Текущее название: {safe_title}\n\n"
        f"Введи новое название (или /skip чтобы оставить):",
        reply_markup=get_cancel_keyboard(f"admin_lesson_{lesson_id}"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_lesson_delete_"))
async def callback_lesson_delete(callback: CallbackQuery):
    """Подтверждение удаления урока"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    lesson_id = int(callback.data.split("_")[-1])
    service = get_lesson_service()
    lesson = await service.get_lesson(lesson_id)

    if not lesson:
        await callback.answer("Урок не найден", show_alert=True)
        return

    text = f"⚠️ <b>Удаление урока</b>\n\nТы уверен, что хочешь удалить урок '{lesson.title}'?\n\nВсе фрагменты урока также будут удалены!"
    await callback.message.edit_text(
        text,
        reply_markup=get_confirm_delete_keyboard(
            "lesson", lesson_id, f"admin_lesson_{lesson_id}"
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_lesson_delete_confirm_"))
async def callback_lesson_delete_confirm(callback: CallbackQuery):
    """Подтверждённое удаление урока"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    lesson_id = int(callback.data.split("_")[-1])
    service = get_lesson_service()
    lesson = await service.get_lesson(lesson_id)

    if not lesson:
        await callback.answer("Урок не найден", show_alert=True)
        return

    block_id = lesson.block_id
    success = await service.delete_lesson(lesson_id)
    if success:
        block = await service.get_block(block_id, include_lessons=True)
        await callback.message.edit_text(
            "✅ Урок удалён",
            reply_markup=(
                get_lessons_admin_keyboard(block)
                if block
                else get_admin_main_keyboard()
            ),
        )
    else:
        await callback.answer("Ошибка при удалении", show_alert=True)
    await callback.answer()


# ==================== ФРАГМЕНТЫ ====================


@router.callback_query(
    F.data.startswith("admin_fragment_")
    & ~F.data.startswith("admin_fragment_edit_")
    & ~F.data.startswith("admin_fragment_delete_")
    & ~F.data.startswith("admin_fragment_create_")
    & ~F.data.startswith("admin_fragment_up_")
    & ~F.data.startswith("admin_fragment_down_")
)
async def callback_admin_fragment(callback: CallbackQuery):
    """Показать фрагмент"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    fragment_id = int(callback.data.split("_")[-1])
    service = get_lesson_service()
    fragment = await service.get_fragment(fragment_id)

    if not fragment:
        await callback.answer("Фрагмент не найден", show_alert=True)
        return

    lesson = await service.get_lesson(fragment.lesson_id)
    if not lesson:
        await callback.answer("Урок не найден", show_alert=True)
        return

    fragment_type_text = (
        "📝 Тест" if fragment.fragment_type == FragmentType.TEST else "📚 Теория"
    )
    safe_content = escape_html(fragment.content[:200])
    content_ellipsis = "..." if len(fragment.content) > 200 else ""

    text = f"""📄 <b>Фрагмент #{fragment.order + 1}</b>

<b>Тип:</b> {fragment_type_text}
<b>Порядок:</b> {fragment.order + 1}

<b>Содержание:</b>
{safe_content}{content_ellipsis}"""

    if fragment.fragment_type == FragmentType.TEST and fragment.correct_answer:
        safe_answer = escape_html(fragment.correct_answer)
        text += f"\n\n<b>Правильный ответ:</b> {safe_answer}"

    await callback.message.edit_text(
        text, reply_markup=get_fragment_admin_keyboard(fragment, lesson)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_fragment_create_"))
async def callback_fragment_create_start(callback: CallbackQuery, state: FSMContext):
    """Начало создания фрагмента"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    lesson_id = int(callback.data.split("_")[-1])
    await state.update_data(lesson_id=lesson_id)
    await state.set_state(AdminFragmentStates.waiting_for_type)

    await callback.message.edit_text(
        "📝 <b>Создание фрагмента</b>\n\nВыбери тип фрагмента:",
        reply_markup=get_fragment_type_keyboard(lesson_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("fragment_type_"))
async def callback_fragment_type(callback: CallbackQuery, state: FSMContext):
    """Выбор типа фрагмента"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    fragment_type_str = callback.data.split("_")[-1]
    fragment_type = (
        FragmentType.TEST if fragment_type_str == "test" else FragmentType.THEORY
    )
    await state.update_data(fragment_type=fragment_type)
    await state.set_state(AdminFragmentStates.waiting_for_content)

    data = await state.get_data()
    lesson_id = data["lesson_id"]

    if fragment_type == FragmentType.TEST:
        text = "📝 <b>Создание теста</b>\n\nВведи текст вопроса:"
    else:
        text = "📚 <b>Создание теории</b>\n\nВведи текст фрагмента:"

    await callback.message.edit_text(
        text, reply_markup=get_cancel_keyboard(f"admin_lesson_{lesson_id}")
    )
    await callback.answer()


@router.message(StateFilter(AdminFragmentStates.waiting_for_content))
async def process_fragment_content(message: Message, state: FSMContext):
    """Обработка содержания фрагмента"""
    data = await state.get_data()
    fragment_type = data.get("fragment_type")

    await state.update_data(content=message.text)

    if fragment_type == FragmentType.TEST:
        await state.set_state(AdminFragmentStates.waiting_for_answer)
        await message.answer(
            "Введи правильный ответ на тест:", reply_markup=get_cancel_keyboard()
        )
    else:
        await state.set_state(AdminFragmentStates.waiting_for_order)
        await message.answer(
            "Введи порядковый номер фрагмента (число):",
            reply_markup=get_cancel_keyboard(),
        )


@router.message(StateFilter(AdminFragmentStates.waiting_for_answer))
async def process_fragment_answer(message: Message, state: FSMContext):
    """Обработка правильного ответа для теста"""
    await state.update_data(correct_answer=message.text)
    await state.set_state(AdminFragmentStates.waiting_for_order)
    await message.answer(
        "Введи порядковый номер фрагмента (число):", reply_markup=get_cancel_keyboard()
    )


@router.message(StateFilter(AdminFragmentStates.waiting_for_order))
async def process_fragment_order(message: Message, state: FSMContext):
    """Обработка порядка фрагмента и создание"""
    try:
        order = int(message.text)
        data = await state.get_data()

        service = get_lesson_service()
        lesson_id = data["lesson_id"]
        fragment_type = data["fragment_type"]

        # Проверяем структуру перед созданием
        existing_fragments = await service.get_fragments_by_lesson(lesson_id)
        sorted_fragments = sorted(existing_fragments, key=lambda x: x.order)

        # Если создаем тест, проверяем структуру
        if fragment_type == FragmentType.TEST:
            # Тест не может быть первым или последним
            if order == 0:
                await message.answer(
                    "❌ Тест не может быть первым фрагментом. Он должен быть между двумя фрагментами теории.",
                    reply_markup=get_cancel_keyboard(),
                )
                return

            # Проверяем, что перед тестом есть theory
            prev_fragment = next(
                (f for f in sorted_fragments if f.order == order - 1), None
            )
            if not prev_fragment or prev_fragment.fragment_type != FragmentType.THEORY:
                await message.answer(
                    "❌ Перед тестом должен быть фрагмент теории. Сначала создай фрагмент теории на позиции "
                    + str(order - 1)
                    + ".",
                    reply_markup=get_cancel_keyboard(),
                )
                return

            # Проверяем, что после теста будет theory (или уже есть)
            next_fragment = next(
                (f for f in sorted_fragments if f.order == order), None
            )
            if next_fragment and next_fragment.fragment_type != FragmentType.TEST:
                # Если следующий фрагмент не тест, проверяем что он theory
                if next_fragment.fragment_type != FragmentType.THEORY:
                    await message.answer(
                        "❌ После теста должен быть фрагмент теории. Сначала создай фрагмент теории на позиции "
                        + str(order + 1)
                        + ".",
                        reply_markup=get_cancel_keyboard(),
                    )
                    return

        fragment = await service.create_fragment(
            FragmentCreate(
                lesson_id=lesson_id,
                fragment_type=fragment_type,
                content=data["content"],
                correct_answer=data.get("correct_answer"),
                order=order,
            )
        )

        await state.clear()
        lesson = await service.get_lesson(lesson_id, include_fragments=True)
        await message.answer(
            f"✅ Фрагмент создан!",
            reply_markup=(
                get_fragments_admin_keyboard(lesson)
                if lesson
                else get_admin_main_keyboard()
            ),
        )
    except ValueError:
        await message.answer(
            "❌ Неверный формат числа. Попробуй ещё раз:",
            reply_markup=get_cancel_keyboard(),
        )


@router.callback_query(F.data.startswith("admin_fragment_edit_"))
async def callback_fragment_edit_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования фрагмента"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    fragment_id = int(callback.data.split("_")[-1])
    service = get_lesson_service()
    fragment = await service.get_fragment(fragment_id)

    if not fragment:
        await callback.answer("Фрагмент не найден", show_alert=True)
        return

    await state.update_data(
        editing_fragment_id=fragment_id, lesson_id=fragment.lesson_id
    )
    await state.set_state(AdminFragmentStates.waiting_for_content)

    fragment_type_text = (
        "теста" if fragment.fragment_type == FragmentType.TEST else "теории"
    )
    safe_content = escape_html(fragment.content[:100])

    await callback.message.edit_text(
        f"✏️ <b>Редактирование фрагмента</b>\n\n"
        f"Текущее содержание ({fragment_type_text}):\n{safe_content}...\n\n"
        f"Введи новое содержание (или /skip чтобы оставить):",
        reply_markup=get_cancel_keyboard(f"admin_fragment_{fragment_id}"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_fragment_delete_"))
async def callback_fragment_delete(callback: CallbackQuery):
    """Подтверждение удаления фрагмента"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    fragment_id = int(callback.data.split("_")[-1])
    service = get_lesson_service()
    fragment = await service.get_fragment(fragment_id)

    if not fragment:
        await callback.answer("Фрагмент не найден", show_alert=True)
        return

    text = (
        f"⚠️ <b>Удаление фрагмента</b>\n\nТы уверен, что хочешь удалить этот фрагмент?"
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_confirm_delete_keyboard(
            "fragment", fragment_id, f"admin_fragment_{fragment_id}"
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_fragment_delete_confirm_"))
async def callback_fragment_delete_confirm(callback: CallbackQuery):
    """Подтверждённое удаление фрагмента"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    fragment_id = int(callback.data.split("_")[-1])
    service = get_lesson_service()
    fragment = await service.get_fragment(fragment_id)

    if not fragment:
        await callback.answer("Фрагмент не найден", show_alert=True)
        return

    lesson_id = fragment.lesson_id
    success = await service.delete_fragment(fragment_id)
    if success:
        lesson = await service.get_lesson(lesson_id, include_fragments=True)
        await callback.message.edit_text(
            "✅ Фрагмент удалён",
            reply_markup=(
                get_fragments_admin_keyboard(lesson)
                if lesson
                else get_admin_main_keyboard()
            ),
        )
    else:
        await callback.answer("Ошибка при удалении", show_alert=True)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_fragment_up_"))
async def callback_fragment_up(callback: CallbackQuery):
    """Переместить фрагмент вверх"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    fragment_id = int(callback.data.split("_")[-1])
    service = get_lesson_service()
    fragment = await service.get_fragment(fragment_id)

    if not fragment:
        await callback.answer("Фрагмент не найден", show_alert=True)
        return

    if fragment.order <= 0:
        await callback.answer("Фрагмент уже первый", show_alert=True)
        return

    # Получаем предыдущий фрагмент
    lesson = await service.get_lesson(fragment.lesson_id, include_fragments=True)
    if lesson and lesson.fragments:
        sorted_fragments = sorted(lesson.fragments, key=lambda x: x.order)
        for i, f in enumerate(sorted_fragments):
            if f.id == fragment_id and i > 0:
                prev_fragment = sorted_fragments[i - 1]
                # Меняем порядок местами
                await service.update_fragment(
                    fragment_id, FragmentUpdate(order=prev_fragment.order)
                )
                await service.update_fragment(
                    prev_fragment.id, FragmentUpdate(order=fragment.order)
                )
                break

    await callback.answer("✅ Фрагмент перемещён вверх")
    # Обновляем отображение
    updated_fragment = await service.get_fragment(fragment_id)
    if updated_fragment:
        lesson = await service.get_lesson(updated_fragment.lesson_id)
        await callback.message.edit_text(
            f"✅ Фрагмент перемещён вверх",
            reply_markup=(
                get_fragment_admin_keyboard(updated_fragment, lesson)
                if lesson
                else get_admin_main_keyboard()
            ),
        )


@router.callback_query(F.data.startswith("admin_fragment_down_"))
async def callback_fragment_down(callback: CallbackQuery):
    """Переместить фрагмент вниз"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    fragment_id = int(callback.data.split("_")[-1])
    service = get_lesson_service()
    fragment = await service.get_fragment(fragment_id)

    if not fragment:
        await callback.answer("Фрагмент не найден", show_alert=True)
        return

    # Получаем следующий фрагмент
    lesson = await service.get_lesson(fragment.lesson_id, include_fragments=True)
    if lesson and lesson.fragments:
        sorted_fragments = sorted(lesson.fragments, key=lambda x: x.order)
        for i, f in enumerate(sorted_fragments):
            if f.id == fragment_id and i < len(sorted_fragments) - 1:
                next_fragment = sorted_fragments[i + 1]
                # Меняем порядок местами
                await service.update_fragment(
                    fragment_id, FragmentUpdate(order=next_fragment.order)
                )
                await service.update_fragment(
                    next_fragment.id, FragmentUpdate(order=fragment.order)
                )
                break
        else:
            await callback.answer("Фрагмент уже последний", show_alert=True)
            return

    await callback.answer("✅ Фрагмент перемещён вниз")
    # Обновляем отображение
    updated_fragment = await service.get_fragment(fragment_id)
    if updated_fragment:
        lesson = await service.get_lesson(updated_fragment.lesson_id)
        await callback.message.edit_text(
            f"✅ Фрагмент перемещён вниз",
            reply_markup=(
                get_fragment_admin_keyboard(updated_fragment, lesson)
                if lesson
                else get_admin_main_keyboard()
            ),
        )
