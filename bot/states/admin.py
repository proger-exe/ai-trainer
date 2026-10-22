"""
FSM состояния для админ-панели
"""

from aiogram.fsm.state import State, StatesGroup


class AdminBlockStates(StatesGroup):
    """Состояния для создания/редактирования блока"""

    waiting_for_title = State()
    waiting_for_emoji = State()
    waiting_for_description = State()
    waiting_for_order = State()


class AdminLessonStates(StatesGroup):
    """Состояния для создания/редактирования урока"""

    waiting_for_title = State()
    waiting_for_order = State()


class AdminFragmentStates(StatesGroup):
    """Состояния для создания/редактирования фрагмента"""

    waiting_for_type = State()
    waiting_for_content = State()
    waiting_for_answer = State()  # Для тестов
    waiting_for_order = State()


class AdminOnboardingQuestionStates(StatesGroup):
    """Состояния для создания/редактирования вопроса онбординга"""

    waiting_for_key = State()
    waiting_for_title = State()
    waiting_for_content = State()
    waiting_for_options = State()
    waiting_for_order = State()
    waiting_for_edit_field = State()
    waiting_for_edit_title = State()
    waiting_for_edit_content = State()
    waiting_for_edit_options = State()
    waiting_for_edit_order = State()
