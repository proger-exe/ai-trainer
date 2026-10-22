"""
Расширенные клавиатуры для онбординга с погружением
"""

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import WebAppInfo
from typing import List, Optional
from bot.models.onboarding import OnboardingPhase
from core.config import Config


def get_onboarding_welcome_keyboard(user_id: int = None):
    """Клавиатура приветствия онбординга"""
    builder = InlineKeyboardBuilder()

    # Если есть URL для теста, используем WebApp с user_id
    if Config.ONBOARDING_WEBAPP_URL and user_id:
        test_url = (
            f"{Config.ONBOARDING_WEBAPP_URL}&user_id={user_id}"
            if "?" in Config.ONBOARDING_WEBAPP_URL
            else f"{Config.ONBOARDING_WEBAPP_URL}?user_id={user_id}"
        )
        builder.button(
            text="📝 Пройти тест (+50 баллов)", web_app=WebAppInfo(url=test_url)
        )
    else:
        builder.button(
            text="🚀 Начать знакомство (+50 баллов)",
            callback_data="onboarding_extended_start",
        )
    builder.button(text="⏩ Пропустить", callback_data="onboarding_skip")

    builder.adjust(1)
    return builder.as_markup()


def get_onboarding_question_keyboard(step: int, options: List[str]):
    """Клавиатура с вариантами ответа на вопрос"""
    builder = InlineKeyboardBuilder()

    for i, option in enumerate(options):
        builder.button(text=option, callback_data=f"onboarding_answer_{step}_{i}")

    builder.adjust(1)
    return builder.as_markup()


def get_onboarding_phase_keyboard(phase: OnboardingPhase, step: int = 0):
    """Клавиатура для перехода между фазами"""
    builder = InlineKeyboardBuilder()

    if phase == OnboardingPhase.QUESTIONS:
        builder.button(text="➡️ Далее", callback_data=f"onboarding_next_{step}")
    elif phase == OnboardingPhase.DEMO_LEARNING:
        builder.button(
            text="📚 Попробовать обучение", callback_data="onboarding_demo_learning"
        )
        builder.button(
            text="⏩ Пропустить демо", callback_data="onboarding_skip_demo_learning"
        )
    elif phase == OnboardingPhase.DEMO_TOXIC:
        builder.button(
            text="😤 Попробовать Toxic Chat", callback_data="onboarding_demo_toxic"
        )
        builder.button(
            text="⏩ Пропустить демо", callback_data="onboarding_skip_demo_toxic"
        )
    elif phase == OnboardingPhase.DEMO_TASKS:
        builder.button(
            text="📋 Попробовать анализ", callback_data="onboarding_demo_analysis"
        )
        builder.button(
            text="⏩ Пропустить демо", callback_data="onboarding_skip_demo_analysis"
        )
    elif phase == OnboardingPhase.RECOMMENDATION:
        builder.button(
            text="🎯 Получить рекомендацию",
            callback_data="onboarding_get_recommendation",
        )
    elif phase == OnboardingPhase.GOAL_SETTING:
        builder.button(
            text="🏆 Принять цель: 1000 баллов", callback_data="onboarding_accept_goal"
        )

    builder.adjust(1)
    return builder.as_markup()


def get_onboarding_demo_learning_keyboard():
    """Клавиатура демо-урока"""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="✅ Понятно, продолжить", callback_data="onboarding_demo_learning_done"
    )

    return builder.as_markup()


def get_onboarding_demo_analysis_keyboard():
    """Клавиатура демо-анализа"""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="✅ Понятно, продолжить", callback_data="onboarding_demo_analysis_done"
    )

    return builder.as_markup()


def get_onboarding_recommendation_keyboard(block_id: int, block_title: str):
    """Клавиатура после AI-рекомендации"""
    builder = InlineKeyboardBuilder()

    builder.button(
        text=f"📚 Начать с «{block_title}»",
        callback_data=f"onboarding_start_block_{block_id}",
    )
    builder.button(
        text="📋 Посмотреть все блоки", callback_data="onboarding_view_all_blocks"
    )
    builder.button(text="➡️ Сначала цель", callback_data="onboarding_to_goal")

    builder.adjust(1)
    return builder.as_markup()


def get_onboarding_goal_keyboard():
    """Клавиатура установки цели"""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🏆 Принимаю цель: 1000 баллов!", callback_data="onboarding_accept_goal"
    )
    builder.button(text="ℹ️ Что я получу?", callback_data="onboarding_goal_info")

    builder.adjust(1)
    return builder.as_markup()


def get_onboarding_complete_keyboard():
    """Клавиатура завершения онбординга"""
    builder = InlineKeyboardBuilder()

    builder.button(text="😤 Toxic Chat", callback_data="module_toxic")
    builder.button(text="🏠 Главное меню", callback_data="home")

    builder.adjust(2, 1)
    return builder.as_markup()


def get_webapp_results_keyboard():
    """Клавиатура результата WebApp-теста"""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="Сохранить результаты и вернуться в тг-бот",
        callback_data="webapp_results_done",
    )

    builder.adjust(1)
    return builder.as_markup()


def get_onboarding_progress_indicator(current_phase: OnboardingPhase) -> str:
    """Генерация индикатора прогресса онбординга"""
    phases = [
        (OnboardingPhase.WELCOME, "👋"),
        (OnboardingPhase.QUESTIONS, "❓"),
        (OnboardingPhase.DEMO_LEARNING, "📚"),
        (OnboardingPhase.DEMO_TOXIC, "😤"),
        (OnboardingPhase.DEMO_TASKS, "📋"),
        (OnboardingPhase.RECOMMENDATION, "🎯"),
        (OnboardingPhase.GOAL_SETTING, "🏆"),
        (OnboardingPhase.COMPLETE, "✅"),
    ]

    result = []
    passed = False

    for phase, emoji in phases:
        if phase == current_phase:
            result.append(f"[{emoji}]")
            passed = True
        elif not passed:
            result.append(f"✓")
        else:
            result.append("○")

    return " ".join(result)
