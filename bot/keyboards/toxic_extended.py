"""
Расширенные клавиатуры для Toxic Chat с режимами
"""

from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Optional
from bot.models.toxic import (
    ToxicMode,
    ToxicGoal,
    ToxicScenario,
    GOAL_DETAILS,
    SCENARIO_DETAILS,
    ToxicMission,
)


def get_toxic_mode_keyboard():
    """Клавиатура выбора режима Toxic Chat"""
    builder = InlineKeyboardBuilder()

    builder.button(text="🎮 Свободный режим", callback_data="toxic_mode_free")
    builder.button(text="🎯 Режим миссий", callback_data="toxic_mode_mission")
    builder.button(text="📋 Выбор ситуации", callback_data="toxic_mode_scenario")
    builder.button(text="🏠 Домой", callback_data="home")

    builder.adjust(1)
    return builder.as_markup()


def get_toxic_goals_keyboard(selected_goals: List[ToxicGoal] = None):
    """Клавиатура выбора целей для сессии"""
    if selected_goals is None:
        selected_goals = []

    builder = InlineKeyboardBuilder()

    for goal in ToxicGoal:
        details = GOAL_DETAILS[goal]
        is_selected = goal in selected_goals
        check = "✅ " if is_selected else ""

        builder.button(
            text=f"{check}{details['emoji']} {details['title']}",
            callback_data=f"toxic_goal_{goal.value}",
        )

    # Кнопка продолжения если выбрана хотя бы одна цель
    if selected_goals:
        builder.button(text="➡️ Продолжить", callback_data="toxic_goals_done")

    builder.button(text="⬅️ Назад", callback_data="module_toxic")

    builder.adjust(1)
    return builder.as_markup()


def get_toxic_scenarios_keyboard(page: int = 0, items_per_page: int = 4):
    """Клавиатура выбора сценария"""
    builder = InlineKeyboardBuilder()

    scenarios = list(ToxicScenario)
    total_pages = (len(scenarios) + items_per_page - 1) // items_per_page

    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(scenarios))

    for scenario in scenarios[start_idx:end_idx]:
        details = SCENARIO_DETAILS[scenario]
        builder.button(
            text=f"{details['emoji']} {details['title']}",
            callback_data=f"toxic_scenario_{scenario.value}",
        )

    # Навигация по страницам
    nav_buttons = []
    if page > 0:
        nav_buttons.append(("⬅️", f"toxic_scenarios_page_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(("➡️", f"toxic_scenarios_page_{page + 1}"))

    for text, callback in nav_buttons:
        builder.button(text=text, callback_data=callback)

    builder.button(text="⬅️ К режимам", callback_data="module_toxic")

    if nav_buttons:
        builder.adjust(1, 1, 1, 1, len(nav_buttons), 1)
    else:
        builder.adjust(1)

    return builder.as_markup()


def get_toxic_scenario_confirm_keyboard(scenario: ToxicScenario):
    """Клавиатура подтверждения выбранного сценария"""
    builder = InlineKeyboardBuilder()
    details = SCENARIO_DETAILS[scenario]

    builder.button(
        text="🎯 Выбрать цели", callback_data=f"toxic_scenario_goals_{scenario.value}"
    )
    builder.button(
        text="🚀 Начать сразу", callback_data=f"toxic_scenario_start_{scenario.value}"
    )
    builder.button(text="⬅️ Другой сценарий", callback_data="toxic_mode_scenario")

    builder.adjust(1)
    return builder.as_markup()


def get_toxic_missions_keyboard(
    missions: List[ToxicMission], completed_ids: List[str] = None
):
    """Клавиатура выбора миссии"""
    if completed_ids is None:
        completed_ids = []

    builder = InlineKeyboardBuilder()

    for mission in missions:
        is_completed = mission.id in completed_ids
        status = "✅ " if is_completed else ""
        difficulty_stars = "⭐" * mission.difficulty

        builder.button(
            text=f"{status}{SCENARIO_DETAILS[mission.scenario]['emoji']} {mission.description[:30]}...",
            callback_data=f"toxic_mission_{mission.id}",
        )

    builder.button(text="⬅️ К режимам", callback_data="module_toxic")

    builder.adjust(1)
    return builder.as_markup()


def get_toxic_mission_detail_keyboard(mission: ToxicMission):
    """Клавиатура деталей миссии"""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🚀 Начать миссию", callback_data=f"toxic_mission_start_{mission.id}"
    )
    builder.button(text="⬅️ Другие миссии", callback_data="toxic_mode_mission")

    builder.adjust(1)
    return builder.as_markup()


def get_toxic_session_keyboard(is_demo: bool = False):
    """Клавиатура активной сессии Toxic Chat"""
    builder = InlineKeyboardBuilder()

    if is_demo:
        builder.button(
            text="✅ Понял(а), продолжить онбординг",
            callback_data="onboarding_demo_toxic_done",
        )
    else:
        builder.button(text="🏁 Завершить сессию", callback_data="end_toxic")

    return builder.as_markup()


def get_toxic_result_keyboard(has_mission: bool = False):
    """Клавиатура результатов сессии"""
    builder = InlineKeyboardBuilder()

    builder.button(text="🔄 Ещё сессия", callback_data="module_toxic")

    if has_mission:
        builder.button(text="🎯 Другие миссии", callback_data="toxic_mode_mission")

    builder.button(text="🏠 Домой", callback_data="home")

    builder.adjust(2, 2)
    return builder.as_markup()
