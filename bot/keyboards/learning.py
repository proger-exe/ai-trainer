"""
Клавиатуры для обучающего модуля
"""

from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Optional
from bot.models.lesson import Block, Lesson, Fragment, FragmentType


def get_learning_main_keyboard():
    """Главная клавиатура обучающего модуля"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📚 Выбрать блок", callback_data="learning_blocks")
    builder.button(text="📊 Мой прогресс", callback_data="learning_progress")
    builder.button(text="🏠 Домой", callback_data="home")
    builder.adjust(1)
    return builder.as_markup()


def get_blocks_keyboard(blocks: List[Block], user_progress: dict):
    """Клавиатура выбора блока"""
    builder = InlineKeyboardBuilder()

    for block in blocks:
        block_id = block.id
        completed = user_progress.get(block_id, 0)
        total = len(block.lessons)
        emoji = block.emoji
        status = "✅" if completed == total and total > 0 else f"({completed}/{total})"

        builder.button(
            text=f"{emoji} {block.title} {status}", callback_data=f"block_{block_id}"
        )

    builder.button(text="🔙 Назад", callback_data="module_learning")
    builder.adjust(1)
    return builder.as_markup()


def get_lessons_keyboard(block: Block, completed_lessons: List[int]):
    """Клавиатура выбора урока в блоке"""
    builder = InlineKeyboardBuilder()
    block_id = block.id

    # Сортируем уроки по порядку
    sorted_lessons = sorted(
        [l for l in block.lessons if l.is_active], key=lambda x: x.order
    )

    for lesson in sorted_lessons:
        lesson_id = lesson.id
        status = "✅" if lesson_id in completed_lessons else "📖"

        builder.button(
            text=f"{status} Урок {lesson.order}: {lesson.title[:40]}",
            callback_data=f"lesson_{block_id}_{lesson_id}",
        )

    builder.button(text="🔙 К блокам", callback_data="learning_blocks")
    builder.button(text="🏠 Домой", callback_data="home")
    builder.adjust(1)
    return builder.as_markup()


def get_fragment_keyboard(
    block_id: int,
    lesson_id: int,
    fragment: Fragment,
    has_next: bool,
    is_test: bool = False,
):
    """Клавиатура для фрагмента урока"""
    builder = InlineKeyboardBuilder()

    if is_test:
        # Для теста показываем только кнопку отмены (ответ вводится текстом)
        builder.button(text="❌ Отмена", callback_data=f"lesson_{block_id}_{lesson_id}")
    else:
        # Для теории показываем кнопку "Далее"
        if has_next:
            builder.button(
                text="➡️ Далее",
                callback_data=f"fragment_next_{block_id}_{lesson_id}_{fragment.order}",
            )
        else:
            # Последний фрагмент - можно завершить урок
            builder.button(
                text="✅ Завершить урок (+50 баллов)",
                callback_data=f"complete_lesson_{block_id}_{lesson_id}",
            )

    builder.button(text="📋 К урокам", callback_data=f"block_{block_id}")
    builder.button(text="🏠 Домой", callback_data="home")
    builder.adjust(1, 1, 1)
    return builder.as_markup()


def get_test_result_keyboard(
    block_id: int, lesson_id: int, fragment_order: int, is_correct: bool, has_next: bool
):
    """Клавиатура после проверки теста"""
    builder = InlineKeyboardBuilder()

    if is_correct:
        if has_next:
            builder.button(
                text="➡️ Следующий фрагмент",
                callback_data=f"fragment_next_{block_id}_{lesson_id}_{fragment_order}",
            )
        else:
            builder.button(
                text="✅ Завершить урок (+50 баллов)",
                callback_data=f"complete_lesson_{block_id}_{lesson_id}",
            )
    else:
        builder.button(
            text="🔄 Попробовать снова",
            callback_data=f"fragment_{block_id}_{lesson_id}_{fragment_order}",
        )

    builder.button(text="📋 К урокам", callback_data=f"block_{block_id}")
    builder.button(text="🏠 Домой", callback_data="home")
    builder.adjust(1, 1, 1)
    return builder.as_markup()


def get_lesson_completed_keyboard(block_id: int, lesson_id: int, has_next: bool):
    """Клавиатура после завершения урока"""
    builder = InlineKeyboardBuilder()

    if has_next:
        builder.button(
            text="➡️ Следующий урок", callback_data=f"lesson_next_{block_id}_{lesson_id}"
        )

    builder.button(text="😤 Практика в Toxic Chat", callback_data="module_toxic")
    builder.button(text="📋 К урокам", callback_data=f"block_{block_id}")
    builder.button(text="🏠 Домой", callback_data="home")
    builder.adjust(1)
    return builder.as_markup()


def get_progress_keyboard():
    """Клавиатура страницы прогресса"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📚 Продолжить обучение", callback_data="learning_blocks")
    builder.button(text="😤 Toxic Chat", callback_data="module_toxic")
    builder.button(text="🏠 Домой", callback_data="home")
    builder.adjust(1)
    return builder.as_markup()
