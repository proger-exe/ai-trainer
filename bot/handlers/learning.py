"""
Обработчики для обучающего модуля
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from typing import List
import html

from core.container import Container
from core.database import PointsConfig
from bot.utils.validation import validate_user_id

logger = logging.getLogger(__name__)
from bot.keyboards.learning import (
    get_learning_main_keyboard,
    get_blocks_keyboard,
    get_lessons_keyboard,
    get_fragment_keyboard,
    get_test_result_keyboard,
    get_lesson_completed_keyboard,
    get_progress_keyboard,
)
from bot.models.lesson import FragmentType
from bot.states import TestAnswerStates


router = Router()


def get_lesson_service():
    """Получить LessonService из контейнера"""
    return Container.get_instance().get_lesson_service()


async def get_user_block_progress(user_id: int) -> dict:
    """Получить прогресс пользователя по блокам"""
    service = get_lesson_service()
    blocks = await service.get_all_blocks(include_inactive=False)
    block_progress = {}

    for block in blocks:
        lessons = await service.get_lessons_by_block(block.id)
        completed = 0
        for lesson in lessons:
            progress = await service.get_progress(user_id, lesson.id)
            if progress and progress.completed:
                completed += 1
        block_progress[block.id] = completed

    return block_progress


async def get_completed_lessons_in_block(user_id: int, block_id: int) -> List[int]:
    """Получить список завершённых уроков в блоке"""
    service = get_lesson_service()
    lessons = await service.get_lessons_by_block(block_id)
    completed = []

    for lesson in lessons:
        progress = await service.get_progress(user_id, lesson.id)
        if progress and progress.completed:
            completed.append(lesson.id)

    return completed


async def get_next_lesson(block_id: int, lesson_id: int):
    """Получить следующий урок"""
    service = get_lesson_service()
    lessons = await service.get_lessons_by_block(block_id)
    sorted_lessons = sorted([l for l in lessons if l.is_active], key=lambda x: x.order)

    current_index = None
    for i, lesson in enumerate(sorted_lessons):
        if lesson.id == lesson_id:
            current_index = i
            break

    if current_index is not None and current_index + 1 < len(sorted_lessons):
        return (block_id, sorted_lessons[current_index + 1].id)

    return None


async def check_test_passed(user_id: int, lesson_id: int, fragment_id: int) -> bool:
    """Проверка, пройден ли тест пользователем"""
    service = get_lesson_service()
    lesson = await service.get_lesson(lesson_id, include_fragments=True)

    if not lesson or not lesson.fragments:
        return False

    fragments = sorted(lesson.fragments, key=lambda x: x.order)
    test_fragment = next((f for f in fragments if f.id == fragment_id), None)

    if not test_fragment or test_fragment.fragment_type != FragmentType.TEST:
        return False

    # Проверяем прогресс - если пользователь дошел до фрагмента после теста,
    # значит тест пройден
    progress = await service.get_progress(user_id, lesson_id)
    if progress and progress.current_fragment_id:
        current_fragment = next(
            (f for f in fragments if f.id == progress.current_fragment_id), None
        )
        if current_fragment and current_fragment.order > test_fragment.order:
            return True

    return False


async def render_fragment(
    callback: CallbackQuery,
    state: FSMContext,
    block_id: int,
    lesson_id: int,
    fragment_order: int = 0,
):
    """Отображение фрагмента урока"""
    service = get_lesson_service()
    lesson = await service.get_lesson(lesson_id, include_fragments=True)

    if not lesson:
        await callback.answer("Урок не найден", show_alert=True)
        return

    if not lesson.fragments:
        await callback.answer("В уроке нет фрагментов", show_alert=True)
        return

    fragments = sorted(lesson.fragments, key=lambda x: x.order)

    if fragment_order >= len(fragments):
        await callback.answer("Фрагмент не найден", show_alert=True)
        return

    fragment = fragments[fragment_order]
    user_id = callback.from_user.id

    # Проверяем структуру урока для тестов
    if fragment.fragment_type == FragmentType.TEST:
        # Проверяем, был ли пройден предыдущий фрагмент (theory)

        # Проверяем, пройден ли уже этот тест
        test_passed = await check_test_passed(user_id, lesson_id, fragment.id)
        if test_passed:
            # Тест уже пройден, переходим к следующему фрагменту
            await callback.answer("✅ Тест уже пройден, переходим дальше")
            await render_fragment(
                callback, state, block_id, lesson_id, fragment_order=fragment_order + 1
            )
            return

    # Сохраняем прогресс
    await service.save_progress(user_id, lesson_id, fragment_id=fragment.id)

    # Определяем, есть ли следующий фрагмент
    has_next = fragment_order + 1 < len(fragments)

    # Формируем текст
    if fragment.fragment_type == FragmentType.TEST:
        # Устанавливаем state для обработки ответа на тест
        await state.set_state(TestAnswerStates.waiting_for_answer)
        await state.update_data(
            block_id=block_id,
            lesson_id=lesson_id,
            fragment_id=fragment.id,
            fragment_order=fragment_order,
        )

        text = f"""📝 <b>Тест</b>

{fragment.content}

<b>Введи свой ответ:</b>"""

        await callback.message.edit_text(
            text,
            reply_markup=get_fragment_keyboard(
                block_id, lesson_id, fragment, has_next, is_test=True
            ),
        )
        await callback.answer()
    else:
        # Для теории очищаем state если был установлен для теста
        current_state = await state.get_state()
        if current_state == TestAnswerStates.waiting_for_answer:
            await state.clear()

        text = f"""📚 <b>{lesson.title}</b>

{fragment.content}

<b>Фрагмент {fragment_order + 1}/{len(fragments)}</b>"""

        await callback.message.edit_text(
            text,
            reply_markup=get_fragment_keyboard(
                block_id, lesson_id, fragment, has_next, is_test=False
            ),
        )
        await callback.answer()


@router.callback_query(F.data == "module_learning")
async def callback_learning_start(callback: CallbackQuery, state: FSMContext):
    """Начало обучающего модуля"""
    await state.clear()

    user_id = callback.from_user.id
    service = get_lesson_service()
    container = Container.get_instance()
    points_service = container.get_points_service()

    completed = await service.get_completed_count(user_id)
    total = await service.get_total_lessons_count()
    total_points = await points_service.get_total_points(user_id)

    text = f"""📚 <b>Обучающий модуль</b>

Здесь ты освоишь навыки эффективной коммуникации через тематические блоки.

📊 <b>Твой прогресс:</b> {completed}/{total} уроков
💎 <b>Баллы:</b> {total_points}

За каждый пройденный урок ты получаешь <b>+50 баллов</b>!"""

    await callback.message.edit_text(text, reply_markup=get_learning_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "learning_blocks")
async def callback_learning_blocks(callback: CallbackQuery):
    """Список блоков обучения"""
    user_id = callback.from_user.id
    service = get_lesson_service()
    blocks = await service.get_all_blocks(include_inactive=False)

    # Загружаем уроки для каждого блока
    for block in blocks:
        block.lessons = await service.get_lessons_by_block(block.id)

    user_progress = await get_user_block_progress(user_id)

    text = """📚 <b>Выбери блок для изучения:</b>

Рекомендуем проходить блоки по порядку, но ты можешь выбрать любой."""

    await callback.message.edit_text(
        text, reply_markup=get_blocks_keyboard(blocks, user_progress)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("block_"))
async def callback_select_block(callback: CallbackQuery):
    """Выбор блока — показать уроки"""
    block_id = int(callback.data.split("_")[1])
    service = get_lesson_service()
    block = await service.get_block(block_id, include_lessons=True)

    if not block:
        await callback.answer("Блок не найден", show_alert=True)
        return

    user_id = callback.from_user.id
    completed_lessons = await get_completed_lessons_in_block(user_id, block_id)

    text = f"""{block.emoji} <b>{block.title}</b>

{block.description or ""}

Выбери урок:"""

    await callback.message.edit_text(
        text, reply_markup=get_lessons_keyboard(block, completed_lessons)
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("lesson_") & ~F.data.startswith("lesson_next_")
)
async def callback_select_lesson(callback: CallbackQuery, state: FSMContext):
    """Выбор урока — показать первый фрагмент"""
    parts = callback.data.split("_")
    block_id = int(parts[1])
    lesson_id = int(parts[2])

    await state.clear()
    await render_fragment(callback, state, block_id, lesson_id, fragment_order=0)


@router.callback_query(F.data.startswith("fragment_next_"))
async def callback_next_fragment(callback: CallbackQuery, state: FSMContext):
    """Переход к следующему фрагменту"""
    parts = callback.data.split("_")
    block_id = int(parts[2])
    lesson_id = int(parts[3])
    current_order = int(parts[4])

    # Очищаем state если был установлен для теста
    await state.clear()
    await render_fragment(
        callback, state, block_id, lesson_id, fragment_order=current_order + 1
    )


@router.callback_query(
    F.data.startswith("fragment_") & ~F.data.startswith("fragment_next_")
)
async def callback_fragment(callback: CallbackQuery, state: FSMContext):
    """Показать конкретный фрагмент (для повторной попытки теста)"""
    parts = callback.data.split("_")
    block_id = int(parts[1])
    lesson_id = int(parts[2])
    fragment_order = int(parts[3])

    await render_fragment(
        callback, state, block_id, lesson_id, fragment_order=fragment_order
    )


@router.message(TestAnswerStates.waiting_for_answer)
async def process_test_answer(message: Message, state: FSMContext):
    """Обработка ответа на тест"""
    try:
        user_id = validate_user_id(message.from_user.id)
        data = await state.get_data()

        block_id = data.get("block_id")
        lesson_id = data.get("lesson_id")
        fragment_id = data.get("fragment_id")
        fragment_order = data.get("fragment_order")

        if not all([block_id, lesson_id, fragment_id, fragment_order is not None]):
            logger.warning(
                f"[Learning] Missing data for test answer from user {user_id}"
            )
            await message.answer("❌ Ошибка: потеряны данные. Начни урок заново.")
            await state.clear()
            return

        service = get_lesson_service()
        user_answer = message.text.strip() if message.text else ""

        if not user_answer:
            await message.answer("❌ Введи ответ на тест.")
            return

        # Проверяем ответ
        is_correct = await service.check_test_answer(fragment_id, user_answer)

        # Получаем информацию о следующем фрагменте
        lesson = await service.get_lesson(lesson_id, include_fragments=True)
        if not lesson or not lesson.fragments:
            logger.error(f"[Learning] Lesson {lesson_id} not found or has no fragments")
            await message.answer("❌ Ошибка: урок не найден.")
            await state.clear()
            return

        fragments = sorted(lesson.fragments, key=lambda x: x.order)
        has_next = fragment_order + 1 < len(fragments)

        if is_correct:
            # Отмечаем тест как пройденный
            await service.mark_test_passed(user_id, lesson_id, fragment_id)
            logger.info(
                f"[Learning] Test passed for user {user_id}, lesson {lesson_id}, fragment {fragment_id}"
            )

            text = f"""✅ <b>Правильно!</b>

Твой ответ: <i>{html.escape(user_answer)}</i>

Молодец! Переходим к следующему фрагменту."""
            await state.clear()
        else:
            text = f"""❌ <b>Неправильно</b>

Твой ответ: <i>{html.escape(user_answer)}</i>

Попробуй ещё раз!"""

        await message.answer(
            text,
            reply_markup=get_test_result_keyboard(
                block_id, lesson_id, fragment_order, is_correct, has_next
            ),
        )

    except TelegramAPIError as e:
        logger.error(
            f"[Learning] Telegram API error in process_test_answer for user {user_id}: {e}",
            exc_info=True,
        )
        try:
            await message.answer("❌ Ошибка отправки сообщения. Попробуй позже.")
        except Exception:
            pass
    except Exception as e:
        logger.exception(
            f"[Learning] Unexpected error in process_test_answer for user {user_id}: {e}"
        )
        try:
            await message.answer("❌ Произошла ошибка. Попробуй позже.")
        except Exception:
            pass


@router.callback_query(F.data.startswith("fragment_next_"))
async def callback_next_fragment(callback: CallbackQuery, state: FSMContext):
    """Переход к следующему фрагменту"""
    parts = callback.data.split("_")
    block_id = int(parts[2])
    lesson_id = int(parts[3])
    current_order = int(parts[4])

    next_order = current_order + 1
    await render_fragment(
        callback, state, block_id, lesson_id, fragment_order=next_order
    )


@router.callback_query(F.data.startswith("complete_lesson_"))
async def callback_complete_lesson(callback: CallbackQuery, state: FSMContext):
    """Завершение урока"""
    parts = callback.data.split("_")
    block_id = int(parts[2])
    lesson_id = int(parts[3])

    user_id = callback.from_user.id
    service = get_lesson_service()
    lesson = await service.get_lesson(lesson_id, include_fragments=True)

    if not lesson:
        await callback.answer("Урок не найден", show_alert=True)
        return

    # Проверяем, не был ли урок уже пройден
    progress = await service.get_progress(user_id, lesson_id)
    if progress and progress.completed:
        await callback.answer("Урок уже пройден!", show_alert=True)
        return

    # Проверяем, что все тесты пройдены
    if lesson.fragments:
        fragments = sorted(lesson.fragments, key=lambda x: x.order)
        for fragment in fragments:
            if fragment.fragment_type == FragmentType.TEST:
                test_passed = await check_test_passed(user_id, lesson_id, fragment.id)
                if not test_passed:
                    await callback.answer(
                        "⚠️ Сначала пройди все тесты в уроке!", show_alert=True
                    )
                    return

    # Очищаем state
    await state.clear()

    # Завершаем урок и начисляем баллы
    await service.complete_lesson(user_id, lesson_id)

    container = Container.get_instance()
    points_service = container.get_points_service()
    total_points = await points_service.get_total_points(user_id)

    next_lesson = await get_next_lesson(block_id, lesson_id)

    text = f"""✅ <b>Урок завершён!</b>

Урок: {lesson.title}

<b>+{PointsConfig.LESSON_COMPLETE} баллов</b> начислено!
💎 Всего баллов: <b>{total_points}</b>

💡 <i>Рекомендация:</i> закрепи знания на практике в Toxic Chat!"""

    await callback.message.edit_text(
        text,
        reply_markup=get_lesson_completed_keyboard(
            block_id, lesson_id, has_next=next_lesson is not None
        ),
    )
    await callback.answer(f"+{PointsConfig.LESSON_COMPLETE} баллов!")


@router.callback_query(F.data.startswith("lesson_next_"))
async def callback_next_lesson(callback: CallbackQuery, state: FSMContext):
    """Переход к следующему уроку"""
    parts = callback.data.split("_")
    block_id = int(parts[2])
    lesson_id = int(parts[3])

    await state.clear()
    next_l = await get_next_lesson(block_id, lesson_id)
    if next_l:
        await render_fragment(callback, state, next_l[0], next_l[1], fragment_order=0)
    else:
        await callback.answer("Это последний урок", show_alert=True)


@router.callback_query(F.data == "learning_progress")
async def callback_learning_progress(callback: CallbackQuery):
    """Показать прогресс обучения"""
    user_id = callback.from_user.id

    container = Container.get_instance()
    points_service = container.get_points_service()
    service = get_lesson_service()
    toxic_service = container.get_toxic_service()

    total_points = await points_service.get_total_points(user_id)
    points_breakdown = await points_service.get_breakdown(user_id)
    completed_lessons = await service.get_completed_count(user_id)
    total_lessons = await service.get_total_lessons_count()
    toxic_stats = await toxic_service.get_stats(user_id)
    user = await container.get_user_service().get_user(user_id)
    has_grade = user.has_grade if user else False

    lessons_points = points_breakdown.by_source.get("lesson", 0)
    toxic_points = points_breakdown.by_source.get("toxic_chat", 0)
    onboarding_points = points_breakdown.by_source.get("onboarding", 0)

    grade_status = (
        "🏆 Грейд получен!"
        if has_grade
        else f"📈 До грейда: {PointsConfig.GRADE_THRESHOLD - total_points} баллов"
    )

    text = f"""📊 <b>Твой прогресс</b>

💎 <b>Всего баллов:</b> {total_points}
{grade_status}

<b>Источники баллов:</b>
📚 Уроки: {lessons_points} ({completed_lessons}/{total_lessons} уроков)
😤 Toxic Chat: {toxic_points} ({toxic_stats.sessions_count} сессий)
🎯 Онбординг: {onboarding_points}

<b>Статистика Toxic Chat:</b>
🛡️ Границы: {toxic_stats.avg_boundaries}/10
🎭 Манипуляции: {toxic_stats.avg_manipulation}/10  
🤝 Переговоры: {toxic_stats.avg_negotiation}/10

<b>Как заработать баллы:</b>
• Пройти урок — +50 баллов
• Toxic Chat сессия — до 30 баллов
• Онбординг — +35 баллов"""

    await callback.message.edit_text(text, reply_markup=get_progress_keyboard())
    await callback.answer()
