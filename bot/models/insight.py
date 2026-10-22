"""
Модели для Daily Insight
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


class InsightCategory(str, Enum):
    """Категории инсайтов"""

    BOUNDARIES = "boundaries"  # Границы
    MANIPULATION = "manipulation"  # Манипуляции
    NEGOTIATION = "negotiation"  # Переговоры
    EMOTIONS = "emotions"  # Эмоции
    COMMUNICATION = "communication"  # Общение
    CONFLICT = "conflict"  # Конфликты
    SELF_CARE = "self_care"  # Забота о себе


class Insight(BaseModel):
    """Инсайт дня"""

    id: Optional[int] = None
    category: InsightCategory
    title: str
    content: str
    tip: str  # Практический совет
    emoji: str
    is_ai_generated: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserInsight(BaseModel):
    """Просмотренный пользователем инсайт"""

    id: Optional[int] = None
    user_id: int
    insight_id: int
    insight_date: date
    viewed_at: Optional[datetime] = None
    points_earned: int = 0

    class Config:
        from_attributes = True


class InsightStats(BaseModel):
    """Статистика инсайтов пользователя"""

    total_viewed: int = 0
    total_points: int = 0
    streak_days: int = 0  # Серия дней подряд
    best_streak: int = 0
    last_viewed_date: Optional[date] = None


class InsightConfig:
    """Конфигурация инсайтов"""

    POINTS_PER_INSIGHT = 15  # Баллы за просмотр инсайта
    STREAK_BONUS = 5  # Бонус за серию (каждые 7 дней)
    NOTIFICATION_HOUR = 10  # Час отправки уведомления (по UTC)


# Предустановленные инсайты (база, которую можно дополнять AI)
DEFAULT_INSIGHTS = [
    Insight(
        category=InsightCategory.BOUNDARIES,
        title="Право на 'нет'",
        content="Каждый раз, когда вы говорите 'да' чему-то, чему хотите сказать 'нет', вы говорите 'нет' себе.",
        tip="Сегодня попробуйте сказать 'нет' хотя бы одной просьбе, которая вам не подходит.",
        emoji="🛡️",
    ),
    Insight(
        category=InsightCategory.MANIPULATION,
        title="Чувство вины — сигнал",
        content="Если после разговора вы чувствуете необъяснимую вину, возможно, вами манипулировали.",
        tip="Задайте себе вопрос: 'Почему я чувствую вину? Я действительно виноват(а)?'",
        emoji="🎭",
    ),
    Insight(
        category=InsightCategory.NEGOTIATION,
        title="Пауза — ваш союзник",
        content="В переговорах не обязательно отвечать сразу. Пауза даёт время подумать и снижает давление.",
        tip="Используйте фразу 'Мне нужно подумать об этом' — это абсолютно нормально.",
        emoji="⏸️",
    ),
    Insight(
        category=InsightCategory.EMOTIONS,
        title="Эмоции ≠ реальность",
        content="То, что вы чувствуете эмоцию, не означает, что она отражает реальность. Эмоции — информация, а не факт.",
        tip="Когда захлёстывает эмоция, спросите: 'Какой факт стоит за этим чувством?'",
        emoji="💭",
    ),
    Insight(
        category=InsightCategory.COMMUNICATION,
        title="Я-сообщения",
        content="'Ты всегда...' вызывает защиту. 'Я чувствую...' открывает диалог.",
        tip="Замените одно 'Ты...' на 'Я чувствую... когда...'",
        emoji="💬",
    ),
    Insight(
        category=InsightCategory.CONFLICT,
        title="Цель ≠ победа",
        content="В здоровом конфликте цель — не победить, а понять друг друга и найти решение.",
        tip="В следующем споре спросите: 'Какой результат будет хорош для нас обоих?'",
        emoji="🤝",
    ),
    Insight(
        category=InsightCategory.BOUNDARIES,
        title="Границы — не стены",
        content="Границы не отталкивают людей — они показывают, как к вам относиться с уважением.",
        tip="Подумайте: какую границу вы давно хотели установить, но откладывали?",
        emoji="🚧",
    ),
    Insight(
        category=InsightCategory.SELF_CARE,
        title="Забота о себе = эффективность",
        content="Невозможно наливать из пустого кувшина. Забота о себе — не эгоизм, а необходимость.",
        tip="Выделите сегодня 15 минут только для себя — без гаджетов и обязательств.",
        emoji="🧘",
    ),
    Insight(
        category=InsightCategory.MANIPULATION,
        title="DARVO — техника манипулятора",
        content="DARVO: Deny (отрицать), Attack (атаковать), Reverse Victim and Offender (перевернуть роли жертвы и агрессора).",
        tip="Если кто-то вместо извинений начинает обвинять вас — это красный флаг.",
        emoji="🚩",
    ),
    Insight(
        category=InsightCategory.NEGOTIATION,
        title="Интересы vs позиции",
        content="За позицией ('Я хочу повышение') всегда стоит интерес ('Я хочу признания и развития').",
        tip="Попробуйте понять интерес собеседника — это откроет новые варианты решения.",
        emoji="🎯",
    ),
    Insight(
        category=InsightCategory.EMOTIONS,
        title="Названные эмоции теряют силу",
        content="Когда вы называете эмоцию ('Я сейчас злюсь'), она начинает терять над вами власть.",
        tip="Заведите привычку проговаривать: 'Сейчас я чувствую...'",
        emoji="🏷️",
    ),
    Insight(
        category=InsightCategory.COMMUNICATION,
        title="Активное слушание",
        content="Слушать — это не ждать своей очереди говорить. Это стремление понять.",
        tip="В следующем разговоре попробуйте перефразировать сказанное собеседником.",
        emoji="👂",
    ),
    Insight(
        category=InsightCategory.CONFLICT,
        title="Время для разговора",
        content="Важные разговоры лучше не начинать, когда вы устали, голодны или спешите.",
        tip="Перед сложным разговором убедитесь, что у вас есть время и ресурс.",
        emoji="⏰",
    ),
    Insight(
        category=InsightCategory.BOUNDARIES,
        title="'Нет' — полное предложение",
        content="Вам не нужно объяснять или оправдывать своё 'нет'. Оно имеет ценность само по себе.",
        tip="Потренируйтесь произносить 'Нет, спасибо' без объяснений.",
        emoji="✋",
    ),
]
