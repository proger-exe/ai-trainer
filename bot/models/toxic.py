"""
Модели для Toxic Chat
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ToxicMode(str, Enum):
    """Режимы Toxic Chat"""

    FREE = "free"  # Свободный режим - free play
    MISSION = "mission"  # Режим миссий - бот выдаёт ситуацию
    SCENARIO = "scenario"  # Выбор ситуации - пользователь выбирает контекст


class ToxicGoal(str, Enum):
    """Цели для отработки в Toxic Chat"""

    CALM = "calm"  # Сохранять спокойствие
    BOUNDARIES = "boundaries"  # Обозначать границы
    FACTS = "facts"  # Возвращаться к фактам
    DEESCALATE = "deescalate"  # Деэскалация конфликта
    MANIPULATION = "manipulation"  # Распознавание манипуляций


class ToxicScenario(str, Enum):
    """Сценарии для Toxic Chat"""

    BOSS_MANIPULATES = "boss_manipulates"  # Начальник манипулирует
    PASSIVE_AGGRESSIVE = "passive_aggressive"  # Пассивно-агрессивный коллега
    PUSHY_FRIEND = "pushy_friend"  # Напористый друг
    ADVISOR_RELATIVE = "advisor_relative"  # Родственник с советами
    CLIENT_DEMANDS = "client_demands"  # Клиент меняет требования
    OFFENDED_PARTNER = "offended_partner"  # Партнёр с обидами
    TOXIC_CUSTOMER = "toxic_customer"  # Токсичный клиент
    GASLIGHTING = "gaslighting"  # Газлайтинг


# Описания сценариев для UI
SCENARIO_DETAILS = {
    ToxicScenario.BOSS_MANIPULATES: {
        "title": "Начальник манипулирует",
        "description": "Ваш руководитель просит о срочном одолжении в пятницу вечером, ссылаясь на то, сколько он для вас сделал.",
        "emoji": "👔",
    },
    ToxicScenario.PASSIVE_AGGRESSIVE: {
        "title": "Пассивно-агрессивный коллега",
        "description": "Коллега постоянно отпускает едкие комментарии по поводу вашей работы, маскируя их под шутки.",
        "emoji": "😏",
    },
    ToxicScenario.PUSHY_FRIEND: {
        "title": "Напористый друг",
        "description": "Друг предлагает спонтанную идею для совместного отдыха, но игнорирует ваши вопросы и просьбы об уточнении деталей.",
        "emoji": "🙄",
    },
    ToxicScenario.ADVISOR_RELATIVE: {
        "title": "Родственник с советами",
        "description": "На семейном ужине родственник начинает давать непрошеные советы о вашей жизни, карьере или внешнем виде.",
        "emoji": "👵",
    },
    ToxicScenario.CLIENT_DEMANDS: {
        "title": "Клиент меняет требования",
        "description": 'Клиент, для которого вы делаете проект, постоянно просит внести "маленькие правочки", которые выходят за рамки договорённостей.',
        "emoji": "📋",
    },
    ToxicScenario.OFFENDED_PARTNER: {
        "title": "Партнёр с обидами",
        "description": "Ваш партнёр обижается и манипулирует чувством вины, когда вы хотите провести время отдельно от него.",
        "emoji": "💔",
    },
    ToxicScenario.TOXIC_CUSTOMER: {
        "title": "Токсичный клиент в чате",
        "description": "Клиент в чате поддержки ведёт себя агрессивно и требует невозможного.",
        "emoji": "😡",
    },
    ToxicScenario.GASLIGHTING: {
        "title": "Газлайтинг",
        "description": "Собеседник отрицает факты и заставляет вас сомневаться в своей памяти и восприятии.",
        "emoji": "🌀",
    },
}

# Описания целей для UI
GOAL_DETAILS = {
    ToxicGoal.CALM: {
        "title": "Сохранять спокойствие",
        "description": "Отработка навыка сохранения эмоционального равновесия",
        "emoji": "🧘",
    },
    ToxicGoal.BOUNDARIES: {
        "title": "Обозначать границы",
        "description": "Практика установления и защиты личных границ",
        "emoji": "🛡️",
    },
    ToxicGoal.FACTS: {
        "title": "Возвращаться к фактам",
        "description": "Навык перевода разговора в конструктивное русло",
        "emoji": "📊",
    },
    ToxicGoal.DEESCALATE: {
        "title": "Деэскалация конфликта",
        "description": "Умение снижать накал эмоций в разговоре",
        "emoji": "🕊️",
    },
    ToxicGoal.MANIPULATION: {
        "title": "Распознавание манипуляций",
        "description": "Тренировка выявления манипулятивных техник",
        "emoji": "🎭",
    },
}


class ToxicMission(BaseModel):
    """Миссия для режима миссий"""

    id: str
    scenario: ToxicScenario
    goals: List[ToxicGoal]
    difficulty: int  # 1-5
    description: str
    success_criteria: str
    bonus_points: int = 0


class ToxicSessionConfig(BaseModel):
    """Конфигурация сессии Toxic Chat"""

    mode: ToxicMode
    scenario: Optional[ToxicScenario] = None
    goals: List[ToxicGoal] = []
    mission: Optional[ToxicMission] = None
    is_demo: bool = False  # Демо-сессия из онбординга


class ToxicSession(BaseModel):
    """Сессия Toxic Chat"""

    id: Optional[int] = None
    user_id: int
    mode: ToxicMode
    scenario: Optional[ToxicScenario] = None
    goals: List[ToxicGoal] = []
    mission_id: Optional[str] = None
    history: List[Dict[str, str]] = []
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    is_active: bool = True

    class Config:
        from_attributes = True


class ToxicResult(BaseModel):
    """Результат сессии Toxic Chat"""

    id: Optional[int] = None
    user_id: int
    session_id: Optional[int] = None
    mode: ToxicMode
    scenario: Optional[ToxicScenario] = None
    boundaries_score: int = 0
    manipulation_score: int = 0
    negotiation_score: int = 0
    goal_scores: Dict[str, int] = {}  # Оценки по выбранным целям
    total_points: int = 0
    feedback: str = ""
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ToxicStats(BaseModel):
    """Статистика Toxic Chat пользователя"""

    sessions_count: int = 0
    total_points: int = 0
    avg_boundaries: float = 0.0
    avg_manipulation: float = 0.0
    avg_negotiation: float = 0.0
    favorite_mode: Optional[ToxicMode] = None
    best_scenario: Optional[ToxicScenario] = None
    completed_missions: int = 0


# Предустановленные миссии
TOXIC_MISSIONS = [
    ToxicMission(
        id="mission_1",
        scenario=ToxicScenario.BOSS_MANIPULATES,
        goals=[ToxicGoal.BOUNDARIES, ToxicGoal.CALM],
        difficulty=2,
        description="Ваш начальник просит вас остаться на выходные. Установите границы, сохраняя профессионализм.",
        success_criteria="Откажите от сверхурочной работы, не испортив отношения",
        bonus_points=5,
    ),
    ToxicMission(
        id="mission_2",
        scenario=ToxicScenario.PASSIVE_AGGRESSIVE,
        goals=[ToxicGoal.FACTS, ToxicGoal.DEESCALATE],
        difficulty=3,
        description="Коллега снова отпустил едкий комментарий на совещании. Переведите разговор в конструктивное русло.",
        success_criteria="Получите извинения или признание некорректного поведения",
        bonus_points=7,
    ),
    ToxicMission(
        id="mission_3",
        scenario=ToxicScenario.CLIENT_DEMANDS,
        goals=[ToxicGoal.BOUNDARIES, ToxicGoal.FACTS],
        difficulty=3,
        description="Клиент требует срочные правки без доплаты. Защитите свои интересы.",
        success_criteria="Добейтесь оплаты дополнительной работы или отказа от неё",
        bonus_points=8,
    ),
    ToxicMission(
        id="mission_4",
        scenario=ToxicScenario.GASLIGHTING,
        goals=[ToxicGoal.MANIPULATION, ToxicGoal.FACTS],
        difficulty=4,
        description="Собеседник утверждает, что вы никогда не договаривались о встрече, хотя у вас есть переписка.",
        success_criteria="Не позвольте себя запутать и сохраните уверенность в фактах",
        bonus_points=10,
    ),
    ToxicMission(
        id="mission_5",
        scenario=ToxicScenario.OFFENDED_PARTNER,
        goals=[ToxicGoal.CALM, ToxicGoal.BOUNDARIES],
        difficulty=3,
        description="Партнёр обиделся, что вы хотите провести вечер с друзьями. Объясните свою позицию.",
        success_criteria="Договоритесь о компромиссе без чувства вины",
        bonus_points=6,
    ),
]
