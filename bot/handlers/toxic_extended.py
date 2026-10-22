"""
Расширенный Toxic Chat с тремя режимами
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
import json

from core.container import Container
from core.bridge import bridge

logger = logging.getLogger(__name__)
from bot.keyboards.toxic_extended import (
    get_toxic_mode_keyboard,
    get_toxic_goals_keyboard,
    get_toxic_scenarios_keyboard,
    get_toxic_scenario_confirm_keyboard,
    get_toxic_missions_keyboard,
    get_toxic_mission_detail_keyboard,
    get_toxic_session_keyboard,
    get_toxic_result_keyboard,
)
from bot.keyboards import get_home_keyboard
from bot.models.toxic import (
    ToxicMode,
    ToxicGoal,
    ToxicScenario,
    GOAL_DETAILS,
    SCENARIO_DETAILS,
    TOXIC_MISSIONS,
)

router = Router()


class ToxicExtendedStates(StatesGroup):
    """Состояния расширенного Toxic Chat"""

    selecting_mode = State()
    selecting_goals = State()
    selecting_scenario = State()
    selecting_mission = State()
    in_session = State()


async def get_completed_missions(user_id: int) -> list:
    """Получить список выполненных миссий"""
    container = Container.get_instance()
    db = container.get_db()

    async with db.get_connection() as conn:
        async with conn.execute(
            """
            SELECT DISTINCT mission_id FROM toxic_sessions 
            WHERE user_id = ? AND mission_id IS NOT NULL AND is_active = 0
        """,
            (user_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def save_toxic_session_config(user_id: int, config: dict):
    """Сохранить конфигурацию сессии"""
    container = Container.get_instance()
    db = container.get_db()

    async with db.get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO toxic_sessions 
            (user_id, mode, scenario, goals, mission_id, is_demo, started_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 1)
        """,
            (
                user_id,
                config.get("mode", "free"),
                config.get("scenario"),
                json.dumps(config.get("goals", []), ensure_ascii=False),
                config.get("mission_id"),
                1 if config.get("is_demo") else 0,
            ),
        )
        await conn.commit()


@router.callback_query(F.data == "module_toxic")
async def callback_toxic_start(callback: CallbackQuery, state: FSMContext):
    """Начало модуля Toxic Chat - выбор режима"""
    user_id = callback.from_user.id

    # Проверяем активную сессию
    container = Container.get_instance()
    db = container.get_db()
    context = await db.get_toxic_context(user_id)

    if context and context.get("history"):
        # Есть активная сессия - продолжаем
        await state.set_state(ToxicExtendedStates.in_session)
        text = "😤 Продолжаем сессию с токсичным собеседником. Напиши сообщение:"
        await callback.message.edit_text(
            text, reply_markup=get_toxic_session_keyboard()
        )
    else:
        # Показываем выбор режима
        await state.set_state(ToxicExtendedStates.selecting_mode)

        text = """😤 <b>Toxic Chat</b>

Выбери режим практики:

<b>🎮 Свободный режим</b>
Общение без заданий. Просто практикуйся!

<b>🎯 Режим миссий</b>
Конкретные задания с целями и бонусными баллами.

<b>📋 Выбор ситуации</b>
Выбери сценарий и цели для отработки."""

        await callback.message.edit_text(text, reply_markup=get_toxic_mode_keyboard())

    await callback.answer()


# ==================== СВОБОДНЫЙ РЕЖИМ ====================


@router.callback_query(F.data == "toxic_mode_free")
async def callback_toxic_free_mode(callback: CallbackQuery, state: FSMContext):
    """Запуск свободного режима"""
    user_id = callback.from_user.id

    await state.set_state(ToxicExtendedStates.in_session)
    await state.update_data(
        mode=ToxicMode.FREE.value, scenario=None, goals=[], mission_id=None
    )

    # Сохраняем конфигурацию сессии
    await save_toxic_session_config(user_id, {"mode": ToxicMode.FREE.value})

    text = """😤 <b>Свободный режим</b>

Ты будешь общаться с токсичным собеседником. Твоя задача — справиться с ситуацией по своему усмотрению.

В конце сессии получишь анализ своего поведения и баллы.

Токсичный собеседник начинает диалог..."""

    await callback.message.edit_text(text, reply_markup=get_toxic_session_keyboard())

    # Запускаем сессию
    command = f"START_TOXIC {user_id}&&free&& => TOXIC"
    bridge.send_to_atlant(command)

    await callback.answer()


# ==================== РЕЖИМ МИССИЙ ====================


@router.callback_query(F.data == "toxic_mode_mission")
async def callback_toxic_mission_mode(callback: CallbackQuery, state: FSMContext):
    """Выбор миссии"""
    user_id = callback.from_user.id

    await state.set_state(ToxicExtendedStates.selecting_mission)

    # Получаем выполненные миссии
    completed = await get_completed_missions(user_id)

    text = """🎯 <b>Режим миссий</b>

Выполняй задания и получай бонусные баллы!

Каждая миссия имеет:
• Конкретную ситуацию
• Цели для отработки
• Критерии успеха
• Бонусные баллы"""

    await callback.message.edit_text(
        text, reply_markup=get_toxic_missions_keyboard(TOXIC_MISSIONS, completed)
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("toxic_mission_") & ~F.data.startswith("toxic_mission_start_")
)
async def callback_toxic_mission_detail(callback: CallbackQuery, state: FSMContext):
    """Детали миссии"""
    mission_id = callback.data.replace("toxic_mission_", "")

    # Находим миссию
    mission = next((m for m in TOXIC_MISSIONS if m.id == mission_id), None)
    if not mission:
        await callback.answer("Миссия не найдена", show_alert=True)
        return

    scenario_info = SCENARIO_DETAILS[mission.scenario]
    goals_text = "\n".join(
        [
            f"• {GOAL_DETAILS[g]['emoji']} {GOAL_DETAILS[g]['title']}"
            for g in mission.goals
        ]
    )

    difficulty_stars = "⭐" * mission.difficulty + "☆" * (5 - mission.difficulty)

    text = f"""🎯 <b>Миссия</b>

{scenario_info["emoji"]} <b>{scenario_info["title"]}</b>

{mission.description}

<b>Цели:</b>
{goals_text}

<b>Критерий успеха:</b>
{mission.success_criteria}

<b>Сложность:</b> {difficulty_stars}
<b>Бонус:</b> +{mission.bonus_points} баллов"""

    await state.update_data(selected_mission=mission_id)

    await callback.message.edit_text(
        text, reply_markup=get_toxic_mission_detail_keyboard(mission)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("toxic_mission_start_"))
async def callback_toxic_mission_start(callback: CallbackQuery, state: FSMContext):
    """Запуск миссии"""
    user_id = callback.from_user.id
    mission_id = callback.data.replace("toxic_mission_start_", "")

    # Находим миссию
    mission = next((m for m in TOXIC_MISSIONS if m.id == mission_id), None)
    if not mission:
        await callback.answer("Миссия не найдена", show_alert=True)
        return

    await state.set_state(ToxicExtendedStates.in_session)
    await state.update_data(
        mode=ToxicMode.MISSION.value,
        scenario=mission.scenario.value,
        goals=[g.value for g in mission.goals],
        mission_id=mission_id,
    )

    # Сохраняем конфигурацию
    await save_toxic_session_config(
        user_id,
        {
            "mode": ToxicMode.MISSION.value,
            "scenario": mission.scenario.value,
            "goals": [g.value for g in mission.goals],
            "mission_id": mission_id,
        },
    )

    scenario_info = SCENARIO_DETAILS[mission.scenario]
    goals_text = ", ".join([GOAL_DETAILS[g]["title"] for g in mission.goals])

    text = f"""🎯 <b>Миссия запущена!</b>

{scenario_info["emoji"]} <b>{scenario_info["title"]}</b>

<b>Твои цели:</b> {goals_text}

<b>Критерий успеха:</b>
{mission.success_criteria}

Токсичный собеседник начинает диалог..."""

    await callback.message.edit_text(text, reply_markup=get_toxic_session_keyboard())

    # Формируем контекст для модели
    context_data = {
        "scenario": mission.scenario.value,
        "scenario_title": scenario_info["title"],
        "scenario_description": scenario_info["description"],
        "goals": [g.value for g in mission.goals],
        "mission_description": mission.description,
    }
    context_json = json.dumps(context_data, ensure_ascii=False)

    # Запускаем сессию с контекстом
    command = f"START_TOXIC {user_id}&&mission&&{context_json} => TOXIC"
    bridge.send_to_atlant(command)

    await callback.answer()


# ==================== ВЫБОР СИТУАЦИИ ====================


@router.callback_query(F.data == "toxic_mode_scenario")
async def callback_toxic_scenario_mode(callback: CallbackQuery, state: FSMContext):
    """Выбор сценария"""
    await state.set_state(ToxicExtendedStates.selecting_scenario)
    await state.update_data(selected_goals=[])

    text = """📋 <b>Выбор ситуации</b>

Выбери сценарий для практики:"""

    await callback.message.edit_text(text, reply_markup=get_toxic_scenarios_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("toxic_scenarios_page_"))
async def callback_toxic_scenarios_page(callback: CallbackQuery):
    """Переключение страницы сценариев"""
    page = int(callback.data.replace("toxic_scenarios_page_", ""))

    text = """📋 <b>Выбор ситуации</b>

Выбери сценарий для практики:"""

    await callback.message.edit_text(
        text, reply_markup=get_toxic_scenarios_keyboard(page)
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("toxic_scenario_")
    & ~F.data.startswith("toxic_scenario_goals_")
    & ~F.data.startswith("toxic_scenario_start_")
)
async def callback_toxic_scenario_select(callback: CallbackQuery, state: FSMContext):
    """Выбор сценария - показ деталей"""
    scenario_value = callback.data.replace("toxic_scenario_", "")

    try:
        scenario = ToxicScenario(scenario_value)
    except ValueError:
        await callback.answer("Сценарий не найден", show_alert=True)
        return

    details = SCENARIO_DETAILS[scenario]

    text = f"""{details["emoji"]} <b>{details["title"]}</b>

{details["description"]}

Выбери, как продолжить:"""

    await state.update_data(selected_scenario=scenario_value)

    await callback.message.edit_text(
        text, reply_markup=get_toxic_scenario_confirm_keyboard(scenario)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("toxic_scenario_goals_"))
async def callback_toxic_scenario_goals(callback: CallbackQuery, state: FSMContext):
    """Выбор целей для сценария"""
    scenario_value = callback.data.replace("toxic_scenario_goals_", "")

    await state.set_state(ToxicExtendedStates.selecting_goals)
    await state.update_data(selected_scenario=scenario_value, selected_goals=[])

    text = """🎯 <b>Выбери цели для отработки</b>

Можешь выбрать несколько целей:"""

    await callback.message.edit_text(text, reply_markup=get_toxic_goals_keyboard([]))
    await callback.answer()


@router.callback_query(F.data.startswith("toxic_goal_"))
async def callback_toxic_goal_toggle(callback: CallbackQuery, state: FSMContext):
    """Переключение выбора цели"""
    goal_value = callback.data.replace("toxic_goal_", "")

    data = await state.get_data()
    selected_goals = data.get("selected_goals", [])

    # Переключаем выбор
    try:
        goal = ToxicGoal(goal_value)
        if goal in selected_goals:
            selected_goals.remove(goal)
        else:
            selected_goals.append(goal)

        await state.update_data(selected_goals=selected_goals)

        text = """🎯 <b>Выбери цели для отработки</b>

Можешь выбрать несколько целей:"""

        await callback.message.edit_text(
            text, reply_markup=get_toxic_goals_keyboard(selected_goals)
        )
    except ValueError:
        await callback.answer("Цель не найдена", show_alert=True)

    await callback.answer()


@router.callback_query(F.data == "toxic_goals_done")
async def callback_toxic_goals_done(callback: CallbackQuery, state: FSMContext):
    """Цели выбраны - запуск сессии"""
    user_id = callback.from_user.id
    data = await state.get_data()

    scenario_value = data.get("selected_scenario")
    selected_goals = data.get("selected_goals", [])

    if not scenario_value:
        await callback.answer("Сценарий не выбран", show_alert=True)
        return

    scenario = ToxicScenario(scenario_value)
    scenario_info = SCENARIO_DETAILS[scenario]

    await state.set_state(ToxicExtendedStates.in_session)
    await state.update_data(
        mode=ToxicMode.SCENARIO.value,
        scenario=scenario_value,
        goals=[g.value for g in selected_goals],
        mission_id=None,
    )

    # Сохраняем конфигурацию
    await save_toxic_session_config(
        user_id,
        {
            "mode": ToxicMode.SCENARIO.value,
            "scenario": scenario_value,
            "goals": [g.value for g in selected_goals],
        },
    )

    goals_text = ", ".join([GOAL_DETAILS[g]["title"] for g in selected_goals])

    text = f"""📋 <b>Сессия настроена!</b>

{scenario_info["emoji"]} <b>{scenario_info["title"]}</b>

<b>Твои цели:</b> {goals_text}

Токсичный собеседник начинает диалог..."""

    await callback.message.edit_text(text, reply_markup=get_toxic_session_keyboard())

    # Формируем контекст для модели
    context_data = {
        "scenario": scenario_value,
        "scenario_title": scenario_info["title"],
        "scenario_description": scenario_info["description"],
        "goals": [g.value for g in selected_goals],
    }
    context_json = json.dumps(context_data, ensure_ascii=False)

    # Запускаем сессию с контекстом
    command = f"START_TOXIC {user_id}&&scenario&&{context_json} => TOXIC"
    bridge.send_to_atlant(command)

    await callback.answer()


@router.callback_query(F.data.startswith("toxic_scenario_start_"))
async def callback_toxic_scenario_start_direct(
    callback: CallbackQuery, state: FSMContext
):
    """Запуск сценария без выбора целей"""
    user_id = callback.from_user.id
    scenario_value = callback.data.replace("toxic_scenario_start_", "")

    scenario = ToxicScenario(scenario_value)
    scenario_info = SCENARIO_DETAILS[scenario]

    await state.set_state(ToxicExtendedStates.in_session)
    await state.update_data(
        mode=ToxicMode.SCENARIO.value,
        scenario=scenario_value,
        goals=[],
        mission_id=None,
    )

    # Сохраняем конфигурацию
    await save_toxic_session_config(
        user_id,
        {"mode": ToxicMode.SCENARIO.value, "scenario": scenario_value, "goals": []},
    )

    text = f"""📋 <b>Сессия запущена!</b>

{scenario_info["emoji"]} <b>{scenario_info["title"]}</b>

{scenario_info["description"]}

Токсичный собеседник начинает диалог..."""

    await callback.message.edit_text(text, reply_markup=get_toxic_session_keyboard())

    # Формируем контекст для модели
    context_data = {
        "scenario": scenario_value,
        "scenario_title": scenario_info["title"],
        "scenario_description": scenario_info["description"],
        "goals": [],
    }
    context_json = json.dumps(context_data, ensure_ascii=False)

    # Запускаем сессию с контекстом
    command = f"START_TOXIC {user_id}&&scenario&&{context_json} => TOXIC"
    bridge.send_to_atlant(command)

    await callback.answer()


# ==================== ОБРАБОТКА СООБЩЕНИЙ В СЕССИИ ====================


@router.message(StateFilter(ToxicExtendedStates.in_session), F.text)
async def process_toxic_message(message: Message, state: FSMContext):
    """Обработка сообщения в сессии"""
    from bot.utils.validation import validate_user_id
    from aiogram.exceptions import TelegramAPIError

    try:
        user_id = validate_user_id(message.from_user.id)
        user_message = message.text

        if not user_message or not user_message.strip():
            await message.answer("❌ Сообщение не может быть пустым.")
            return

        logger.debug(f"[ToxicExtended] Processing message from user {user_id}")

        # Показываем загрузку
        loading_msg = await message.answer("⏳ Токсичный собеседник печатает...")
        loading_msg_id = loading_msg.message_id

        # Сохраняем message_id для редактирования
        container = Container.get_instance()
        db = container.get_db()
        context = await db.get_toxic_context(user_id) or {}
        context["loading_msg_id"] = loading_msg_id
        context["loading_chat_id"] = message.chat.id
        await db.save_toxic_context(user_id, context, session_active=True)

        # Получаем данные сессии
        data = await state.get_data()
        mode = data.get("mode", "free")
        scenario = data.get("scenario")
        goals = data.get("goals", [])

        # Отправляем команду в модель
        command = f"TOXIC_MESSAGE {user_id}&&{user_message} => TOXIC"
        bridge.send_to_atlant(command)

    except TelegramAPIError as e:
        logger.error(
            f"[ToxicExtended] Telegram API error in process_toxic_message for user {user_id}: {e}",
            exc_info=True,
        )
        try:
            await message.answer("❌ Ошибка отправки сообщения. Попробуй позже.")
        except Exception:
            pass
    except Exception as e:
        logger.exception(
            f"[ToxicExtended] Unexpected error in process_toxic_message for user {user_id}: {e}"
        )
        try:
            await message.answer("❌ Произошла ошибка. Попробуй позже.")
        except Exception:
            pass


@router.callback_query(F.data == "end_toxic")
async def callback_end_toxic(callback: CallbackQuery, state: FSMContext):
    """Завершение сессии"""
    from bot.utils.validation import validate_user_id

    try:
        user_id = validate_user_id(callback.from_user.id)
        logger.info(f"[ToxicExtended] Ending session for user {user_id}")

        # Получаем данные сессии для анализа
        data = await state.get_data()
        mode = data.get("mode", "free")
        scenario = data.get("scenario")
        goals = data.get("goals", [])
        mission_id = data.get("mission_id")

        # Сохраняем message_id для редактирования
        loading_msg_id = callback.message.message_id
        loading_chat_id = callback.message.chat.id

        container = Container.get_instance()
        db = container.get_db()
        context = await db.get_toxic_context(user_id) or {}
        context["analysis_loading_msg_id"] = loading_msg_id
        context["analysis_loading_chat_id"] = loading_chat_id
        context["session_mode"] = mode
        context["session_scenario"] = scenario
        context["session_goals"] = goals
        context["session_mission_id"] = mission_id
        await db.save_toxic_context(user_id, context, session_active=True)

        await callback.message.edit_text("⏳ Анализирую твоё поведение...")

        # Формируем контекст для анализа
        analysis_context = {
            "mode": mode,
            "scenario": scenario,
            "goals": goals,
            "mission_id": mission_id,
        }
        analysis_json = json.dumps(analysis_context, ensure_ascii=False)

        # Отправляем команду на завершение с контекстом
        command = f"END_TOXIC_EXTENDED {user_id}&&{analysis_json} => TOXIC"
        bridge.send_to_atlant(command)

        await state.clear()
        await callback.answer()

    except TelegramBadRequest as e:
        logger.warning(f"[ToxicExtended] Cannot edit message for user {user_id}: {e}")
        try:
            await callback.message.answer("⏳ Анализирую твоё поведение...")
            await callback.answer()
        except Exception:
            pass
    except TelegramAPIError as e:
        logger.error(
            f"[ToxicExtended] Telegram API error ending session for user {user_id}: {e}",
            exc_info=True,
        )
        await callback.answer(
            "❌ Ошибка завершения сессии. Попробуй позже.", show_alert=True
        )
    except Exception as e:
        logger.exception(
            f"[ToxicExtended] Unexpected error ending session for user {user_id}: {e}"
        )
        await callback.answer("❌ Произошла ошибка. Попробуй позже.", show_alert=True)
