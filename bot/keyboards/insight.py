"""
Клавиатуры для Daily Insight
"""

from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Optional
from bot.models.insight import InsightCategory


def get_insight_keyboard(insight_id: int, has_points: bool = True):
    """Клавиатура инсайта дня"""
    builder = InlineKeyboardBuilder()

    if has_points:
        builder.button(
            text="💎 Получить +15 баллов", callback_data=f"insight_claim_{insight_id}"
        )

    builder.button(text="🏠 Домой", callback_data="home")

    builder.adjust(1)
    return builder.as_markup()


def get_insight_claimed_keyboard():
    """Клавиатура после получения баллов за инсайт"""
    builder = InlineKeyboardBuilder()

    builder.button(text="😤 Попрактиковать в Toxic Chat", callback_data="module_toxic")
    builder.button(text="🏠 Домой", callback_data="home")

    builder.adjust(1)
    return builder.as_markup()


def get_insight_already_viewed_keyboard():
    """Клавиатура если инсайт уже просмотрен сегодня"""
    builder = InlineKeyboardBuilder()

    builder.button(text="🏠 Домой", callback_data="home")

    builder.adjust(2)
    return builder.as_markup()


def get_insight_settings_keyboard(is_enabled: bool = True):
    """Клавиатура настроек уведомлений об инсайтах"""
    builder = InlineKeyboardBuilder()

    status = "✅" if is_enabled else "❌"
    action = "Отключить" if is_enabled else "Включить"

    builder.button(
        text=f"{status} {action} ежедневные инсайты", callback_data="insight_toggle"
    )
    builder.button(text="⏰ Изменить время", callback_data="insight_change_time")
    builder.button(text="⬅️ Назад", callback_data="my_profile")

    builder.adjust(1)
    return builder.as_markup()


def get_insight_time_keyboard():
    """Клавиатура выбора времени уведомления"""
    builder = InlineKeyboardBuilder()

    times = ["08:00", "09:00", "10:00", "12:00", "18:00", "20:00"]

    for time in times:
        builder.button(text=time, callback_data=f"insight_time_{time.replace(':', '')}")

    builder.button(text="⬅️ Назад", callback_data="insight_settings")

    builder.adjust(3, 3, 1)
    return builder.as_markup()


def get_insight_category_keyboard():
    """Клавиатура выбора категории инсайтов (для просмотра архива)"""
    builder = InlineKeyboardBuilder()

    categories = {
        InsightCategory.BOUNDARIES: "🛡️ Границы",
        InsightCategory.MANIPULATION: "🎭 Манипуляции",
        InsightCategory.NEGOTIATION: "🤝 Переговоры",
        InsightCategory.EMOTIONS: "💭 Эмоции",
        InsightCategory.COMMUNICATION: "💬 Общение",
        InsightCategory.CONFLICT: "⚔️ Конфликты",
        InsightCategory.SELF_CARE: "🧘 Забота о себе",
    }

    for category, title in categories.items():
        builder.button(text=title, callback_data=f"insight_category_{category.value}")

    builder.button(text="⬅️ Назад", callback_data="home")

    builder.adjust(2, 2, 2, 1, 1)
    return builder.as_markup()
