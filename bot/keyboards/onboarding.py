"""
Клавиатуры для онбординга
"""

from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_onboarding_start_keyboard():
    """Клавиатура начала онбординга"""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🚀 Начать знакомство (+35 баллов)", callback_data="onboarding_start"
    )
    builder.button(text="⏩ Пропустить", callback_data="onboarding_skip")
    builder.adjust(1)
    return builder.as_markup()


def get_onboarding_step_keyboard(step: int, total_steps: int):
    """Клавиатура шага онбординга"""
    builder = InlineKeyboardBuilder()

    if step < total_steps:
        builder.button(text="➡️ Далее", callback_data=f"onboarding_step_{step + 1}")
    else:
        builder.button(
            text="✅ Завершить онбординг", callback_data="onboarding_complete"
        )

    builder.adjust(1)
    return builder.as_markup()


def get_onboarding_question_keyboard(step: int, options: list):
    """Клавиатура с вариантами ответа"""
    builder = InlineKeyboardBuilder()

    for i, option in enumerate(options):
        builder.button(text=option, callback_data=f"onboarding_answer_{step}_{i}")

    builder.adjust(1)
    return builder.as_markup()
