"""
Клавиатуры для модуля токсичного собеседника
"""

from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_toxic_keyboard():
    """Клавиатура для модуля токсичного собеседника (только завершение)"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🏁 Завершить сессию", callback_data="end_toxic")
    return builder.as_markup()


def get_toxic_no_keyboard():
    """Клавиатура без кнопок (для обычных сообщений)"""
    return None
