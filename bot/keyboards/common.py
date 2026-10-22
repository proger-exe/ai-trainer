"""
Общие клавиатуры
"""

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import WebAppInfo
from core.config import Config


def get_main_keyboard(show_test_button: bool = False):
    """Клавиатура главного меню"""
    builder = InlineKeyboardBuilder()

    # Кнопка теста (если настроен URL)
    if show_test_button and Config.ONBOARDING_WEBAPP_URL:
        builder.button(
            text="📝 Пройти тест", web_app=WebAppInfo(url=Config.ONBOARDING_WEBAPP_URL)
        )

    builder.button(text="📚 Обучение", callback_data="module_learning")
    builder.button(text="😤 Toxic Chat", callback_data="module_toxic")
    builder.button(text="📋 Разбор ситуации", callback_data="module_analysis")
    builder.button(text="💡 Daily Insight", callback_data="daily_insight")
    builder.button(text="💬 Нетворк-чат", callback_data="module_network")
    builder.button(text="👤 Мой профиль", callback_data="my_profile")
    builder.button(text="🏆 Лидерборд", callback_data="leaderboard")
    builder.button(text="ℹ️ Помощь", callback_data="help")

    if show_test_button and Config.ONBOARDING_WEBAPP_URL:
        builder.adjust(1, 2, 2, 2, 2)
    else:
        builder.adjust(2, 2, 2, 2)
    return builder.as_markup()


def get_home_keyboard():
    """Клавиатура с кнопкой домой"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Домой", callback_data="home")
    builder.adjust(1)
    return builder.as_markup()
