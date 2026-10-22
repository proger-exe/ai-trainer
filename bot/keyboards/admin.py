"""
Клавиатуры для админ-панели
"""

from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Optional
from bot.models.lesson import Block, Lesson, Fragment


def get_admin_main_keyboard():
    """Главная клавиатура админ-панели"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📚 Управление уроками", callback_data="admin_lessons")
    builder.button(text="❓ Управление онбордингом", callback_data="admin_onboarding")
    builder.button(text="👥 Пользователи", callback_data="admin_users")
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="🏠 Домой", callback_data="home")
    builder.adjust(1)
    return builder.as_markup()


def get_blocks_admin_keyboard(blocks: List[Block]):
    """Клавиатура управления блоками"""
    builder = InlineKeyboardBuilder()

    for block in sorted(blocks, key=lambda x: x.order):
        status = "✅" if block.is_active else "❌"
        lessons_count = len(block.lessons) if block.lessons else 0
        builder.button(
            text=f"{status} {block.emoji} {block.title} ({lessons_count} уроков)",
            callback_data=f"admin_block_{block.id}",
        )

    builder.button(text="➕ Добавить блок", callback_data="admin_block_create")
    builder.button(text="🔙 Назад", callback_data="admin_main")
    builder.adjust(1)
    return builder.as_markup()


def get_lessons_admin_keyboard(block: Block):
    """Клавиатура управления уроками в блоке"""
    builder = InlineKeyboardBuilder()

    sorted_lessons = sorted(block.lessons, key=lambda x: x.order)
    for lesson in sorted_lessons:
        status = "✅" if lesson.is_active else "❌"
        fragments_count = len(lesson.fragments) if lesson.fragments else 0
        builder.button(
            text=f"{status} Урок {lesson.order}: {lesson.title[:35]} ({fragments_count} фрагментов)",
            callback_data=f"admin_lesson_{lesson.id}",
        )

    builder.button(
        text="➕ Добавить урок", callback_data=f"admin_lesson_create_{block.id}"
    )
    builder.button(
        text="✏️ Редактировать блок", callback_data=f"admin_block_edit_{block.id}"
    )
    builder.button(
        text="🗑️ Удалить блок", callback_data=f"admin_block_delete_{block.id}"
    )
    builder.button(text="🔙 К блокам", callback_data="admin_lessons")
    builder.adjust(1)
    return builder.as_markup()


def get_fragments_admin_keyboard(lesson: Lesson):
    """Клавиатура управления фрагментами урока"""
    builder = InlineKeyboardBuilder()

    sorted_fragments = sorted(lesson.fragments, key=lambda x: x.order)
    for fragment in sorted_fragments:
        fragment_type_emoji = "📝" if fragment.fragment_type.value == "test" else "📚"
        preview = (
            fragment.content[:30] + "..."
            if len(fragment.content) > 30
            else fragment.content
        )
        builder.button(
            text=f"{fragment_type_emoji} {fragment.order + 1}. {preview}",
            callback_data=f"admin_fragment_{fragment.id}",
        )

    builder.button(
        text="➕ Добавить фрагмент", callback_data=f"admin_fragment_create_{lesson.id}"
    )
    builder.button(
        text="✏️ Редактировать урок", callback_data=f"admin_lesson_edit_{lesson.id}"
    )
    builder.button(
        text="🗑️ Удалить урок", callback_data=f"admin_lesson_delete_{lesson.id}"
    )
    builder.button(text="🔙 К урокам", callback_data=f"admin_block_{lesson.block_id}")
    builder.adjust(1)
    return builder.as_markup()


def get_fragment_admin_keyboard(fragment: Fragment, lesson: Lesson):
    """Клавиатура управления фрагментом"""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="✏️ Редактировать", callback_data=f"admin_fragment_edit_{fragment.id}"
    )
    builder.button(text="⬆️ Вверх", callback_data=f"admin_fragment_up_{fragment.id}")
    builder.button(text="⬇️ Вниз", callback_data=f"admin_fragment_down_{fragment.id}")
    builder.button(
        text="🗑️ Удалить", callback_data=f"admin_fragment_delete_{fragment.id}"
    )
    builder.button(text="🔙 К фрагментам", callback_data=f"admin_lesson_{lesson.id}")
    builder.adjust(2, 1, 1, 1)
    return builder.as_markup()


def get_confirm_delete_keyboard(item_type: str, item_id: int, back_callback: str):
    """Клавиатура подтверждения удаления"""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Да, удалить",
        callback_data=f"admin_{item_type}_delete_confirm_{item_id}",
    )
    builder.button(text="❌ Отмена", callback_data=back_callback)
    builder.adjust(2)
    return builder.as_markup()


def get_cancel_keyboard(callback_data: str = "admin_main"):
    """Клавиатура отмены"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data=callback_data)
    return builder.as_markup()


def get_fragment_type_keyboard(lesson_id: int):
    """Клавиатура выбора типа фрагмента"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📚 Теория", callback_data="fragment_type_theory")
    builder.button(text="📝 Тест", callback_data="fragment_type_test")
    builder.button(text="❌ Отмена", callback_data=f"admin_lesson_{lesson_id}")
    builder.adjust(1)
    return builder.as_markup()


def get_onboarding_questions_keyboard(questions):
    """Клавиатура управления вопросами онбординга"""
    from bot.models.onboarding import OnboardingQuestion

    builder = InlineKeyboardBuilder()

    sorted_questions = sorted(questions, key=lambda x: x.order)
    for question in sorted_questions:
        status = "✅" if question.is_active else "❌"
        preview = (
            question.title[:40] + "..." if len(question.title) > 40 else question.title
        )
        builder.button(
            text=f"{status} {question.order}. {preview}",
            callback_data=f"admin_onboarding_question_{question.id}",
        )

    builder.button(
        text="➕ Добавить вопрос", callback_data="admin_onboarding_question_create"
    )
    builder.button(text="🔙 Назад", callback_data="admin_main")
    builder.adjust(1)
    return builder.as_markup()


def get_onboarding_question_keyboard(question):
    """Клавиатура управления вопросом онбординга"""
    from bot.models.onboarding import OnboardingQuestion

    builder = InlineKeyboardBuilder()
    builder.button(
        text="✏️ Редактировать",
        callback_data=f"admin_onboarding_question_edit_{question.id}",
    )
    builder.button(
        text="🗑️ Удалить",
        callback_data=f"admin_onboarding_question_delete_{question.id}",
    )
    builder.button(text="🔙 К вопросам", callback_data="admin_onboarding")
    builder.adjust(1, 1, 1)
    return builder.as_markup()
