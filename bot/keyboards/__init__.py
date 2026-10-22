"""
Клавиатуры для бота
"""

from bot.keyboards.common import get_main_keyboard, get_home_keyboard
from bot.keyboards.analysis import (
    get_analysis_keyboard,
    get_continue_keyboard,
    get_analysis_no_keyboard,
)
from bot.keyboards.toxic import get_toxic_keyboard, get_toxic_no_keyboard
from bot.keyboards.onboarding import (
    get_onboarding_start_keyboard,
    get_onboarding_step_keyboard,
    get_onboarding_question_keyboard,
)

# Расширенные клавиатуры
from bot.keyboards.toxic_extended import (
    get_toxic_mode_keyboard,
    get_toxic_goals_keyboard,
    get_toxic_scenarios_keyboard,
    get_toxic_session_keyboard,
    get_toxic_result_keyboard,
)
from bot.keyboards.onboarding_extended import (
    get_onboarding_welcome_keyboard,
    get_onboarding_phase_keyboard,
    get_onboarding_complete_keyboard,
)
from bot.keyboards.insight import (
    get_insight_keyboard,
    get_insight_claimed_keyboard,
)

__all__ = [
    # Common
    "get_main_keyboard",
    "get_home_keyboard",
    # Analysis
    "get_analysis_keyboard",
    "get_continue_keyboard",
    "get_analysis_no_keyboard",
    # Toxic (базовые)
    "get_toxic_keyboard",
    "get_toxic_no_keyboard",
    # Toxic (расширенные)
    "get_toxic_mode_keyboard",
    "get_toxic_goals_keyboard",
    "get_toxic_scenarios_keyboard",
    "get_toxic_session_keyboard",
    "get_toxic_result_keyboard",
    # Onboarding (базовые)
    "get_onboarding_start_keyboard",
    "get_onboarding_step_keyboard",
    "get_onboarding_question_keyboard",
    # Onboarding (расширенные)
    "get_onboarding_welcome_keyboard",
    "get_onboarding_phase_keyboard",
    "get_onboarding_complete_keyboard",
    # Insight
    "get_insight_keyboard",
    "get_insight_claimed_keyboard",
]
