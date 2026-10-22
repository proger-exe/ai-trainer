"""
Pydantic модели для типизации данных
"""

from bot.models.user import User, UserCreate, UserUpdate
from bot.models.points import PointsTransaction, PointsBreakdown, PointsResult

# Lesson модели
from bot.models.lesson import (
    Block,
    BlockCreate,
    BlockUpdate,
    Lesson,
    LessonCreate,
    LessonUpdate,
    Fragment,
    FragmentCreate,
    FragmentUpdate,
    FragmentType,
    LessonProgress,
)

# Toxic Chat модели (расширенные)
from bot.models.toxic import (
    ToxicMode,
    ToxicGoal,
    ToxicScenario,
    ToxicSession,
    ToxicResult,
    ToxicStats,
    ToxicMission,
    GOAL_DETAILS,
    SCENARIO_DETAILS,
    TOXIC_MISSIONS,
)

# Onboarding модели
from bot.models.onboarding import (
    OnboardingPhase,
    OnboardingStep,
    OnboardingProgress,
    OnboardingRecommendation,
    OnboardingConfig,
    OnboardingQuestion,
    OnboardingQuestionCreate,
    OnboardingQuestionUpdate,
)

# Insight модели
from bot.models.insight import (
    InsightCategory,
    Insight,
    UserInsight,
    InsightStats,
    InsightConfig,
    DEFAULT_INSIGHTS,
)

__all__ = [
    # User
    "User",
    "UserCreate",
    "UserUpdate",
    # Points
    "PointsTransaction",
    "PointsBreakdown",
    "PointsResult",
    # Lesson
    "Block",
    "BlockCreate",
    "BlockUpdate",
    "Lesson",
    "LessonCreate",
    "LessonUpdate",
    "Fragment",
    "FragmentCreate",
    "FragmentUpdate",
    "FragmentType",
    "LessonProgress",
    # Toxic
    "ToxicMode",
    "ToxicGoal",
    "ToxicScenario",
    "ToxicSession",
    "ToxicResult",
    "ToxicStats",
    "ToxicMission",
    "GOAL_DETAILS",
    "SCENARIO_DETAILS",
    "TOXIC_MISSIONS",
    # Onboarding
    "OnboardingPhase",
    "OnboardingStep",
    "OnboardingProgress",
    "OnboardingRecommendation",
    "OnboardingConfig",
    "OnboardingQuestion",
    "OnboardingQuestionCreate",
    "OnboardingQuestionUpdate",
    # Insight
    "InsightCategory",
    "Insight",
    "UserInsight",
    "InsightStats",
    "InsightConfig",
    "DEFAULT_INSIGHTS",
]
