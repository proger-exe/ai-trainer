"""
Клавиатуры для модуля разбора ситуаций
"""

from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_analysis_keyboard():
    """Клавиатура для модуля анализа"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Домой", callback_data="home")
    builder.button(text="🎯 Указать цель общения", callback_data="set_goal")
    return builder.as_markup()


def get_continue_keyboard():
    """Клавиатура для продолжения разбора (сессия активна)"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🏁 Завершить разбор", callback_data="end_analysis")
    builder.button(text="🏠 Домой", callback_data="home")
    return builder.as_markup()


def get_analysis_no_keyboard():
    """Клавиатура без кнопок (для обычных сообщений в сессии)"""
    return None
