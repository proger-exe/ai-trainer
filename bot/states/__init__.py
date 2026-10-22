"""
FSM состояния для бота
"""

from aiogram.fsm.state import State, StatesGroup
from bot.states.admin import AdminBlockStates, AdminLessonStates, AdminFragmentStates


class AnalysisStates(StatesGroup):
    """Состояния для модуля разбора ситуаций"""

    waiting_for_situation = State()
    waiting_for_goal = State()
    waiting_for_continue = State()


class ToxicStates(StatesGroup):
    """Состояния для модуля токсичного собеседника"""

    in_session = State()


class TestAnswerStates(StatesGroup):
    """Состояние для ввода ответа на тест"""

    waiting_for_answer = State()
