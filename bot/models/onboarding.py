"""
Модели онбординга
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class OnboardingPhase(str, Enum):
    """Фазы онбординга"""

    WELCOME = "welcome"  # Приветствие
    QUESTIONS = "questions"  # Вопросы для анализа
    DEMO_LEARNING = "demo_learning"  # Демо обучения
    DEMO_TOXIC = "demo_toxic"  # Демо токсик-чата
    DEMO_TASKS = "demo_tasks"  # Демо заданий
    RECOMMENDATION = "recommendation"  # Рекомендация от ИИ
    GOAL_SETTING = "goal_setting"  # Установка цели
    COMPLETE = "complete"  # Завершено


class OnboardingStep(BaseModel):
    """Шаг онбординга"""

    phase: OnboardingPhase
    step_number: int
    step_type: str  # "info", "question", "demo", "action"
    title: str
    content: str
    options: Optional[List[str]] = None
    action_callback: Optional[str] = None  # callback_data для действия
    points_reward: int = 0


class OnboardingAnswers(BaseModel):
    """Ответы пользователя на онбординг"""

    user_id: int
    main_challenge: Optional[int] = None  # Основная проблема
    conflict_reaction: Optional[int] = None  # Реакция на конфликт
    time_commitment: Optional[int] = None  # Готовность по времени
    experience_level: Optional[int] = None  # Уровень опыта
    priority_area: Optional[int] = None  # Приоритетная область
    raw_answers: Dict[str, Any] = {}


class OnboardingProgress(BaseModel):
    """Прогресс онбординга"""

    user_id: int
    current_phase: OnboardingPhase = OnboardingPhase.WELCOME
    current_step: int = 0
    answers: OnboardingAnswers
    demo_learning_done: bool = False
    demo_toxic_done: bool = False
    demo_tasks_done: bool = False
    recommended_block: Optional[int] = None
    ai_recommendation: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OnboardingRecommendation(BaseModel):
    """Рекомендация после онбординга"""

    recommended_block_id: int
    recommended_block_title: str
    reasoning: str
    priority_skills: List[str]
    personalized_tip: str


class OnboardingQuestion(BaseModel):
    """Вопрос онбординга"""

    id: Optional[int] = None
    question_key: str
    title: str
    content: str
    options: List[str]
    order: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OnboardingQuestionCreate(BaseModel):
    """Создание вопроса онбординга"""

    question_key: str
    title: str
    content: str
    options: List[str]
    order: int = 0
    is_active: bool = True


class OnboardingQuestionUpdate(BaseModel):
    """Обновление вопроса онбординга"""

    question_key: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    options: Optional[List[str]] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None


# Константы онбординга
class OnboardingConfig:
    """Конфигурация онбординга"""

    TOTAL_POINTS = 50  # Общие баллы за полный онбординг
    PHASE_POINTS = {
        OnboardingPhase.QUESTIONS: 10,
        OnboardingPhase.DEMO_LEARNING: 10,
        OnboardingPhase.DEMO_TOXIC: 15,
        OnboardingPhase.DEMO_TASKS: 10,
        OnboardingPhase.COMPLETE: 5,
    }
    FIRST_GOAL_POINTS = 1000  # Цель для новичка
