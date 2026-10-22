"""
Обработчики для модели TOXIC
"""

import logging
from AtlantSDK import AbstactRouter, Conversation
from core.database import Database
from core.bridge import bridge
from bot.keyboards import get_toxic_keyboard, get_home_keyboard, get_toxic_no_keyboard

logger = logging.getLogger(__name__)

# Создаём роутер для модели TOXIC
router = AbstactRouter("TOXIC")
db = Database()


@router.handler(command="START_TOXIC")
def start_toxic_session(cmd: str, chat: Conversation):
    """
    Обработчик для начала сессии токсичного собеседника
    Формат команды: START_TOXIC user_id&&mode&&context_json
    Где mode: free, mission, scenario
    """
    import json

    try:
        # Парсим команду
        parts = cmd.split("&&")

        # Извлекаем user_id
        cmd_part = parts[0]
        _, user_id = cmd_part.split(" ", 1)
        user_id = int(user_id)

        # Извлекаем режим и контекст
        mode = parts[1] if len(parts) > 1 else "free"
        context_json = parts[2] if len(parts) > 2 else "{}"

        try:
            session_context = json.loads(context_json) if context_json else {}
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(
                f"[Toxic] Failed to parse context_json: {e}, using empty context"
            )
            session_context = {}

        # Формируем промпт в зависимости от режима
        if mode == "free":
            prompt = """Начни диалог с пользователем. Ты токсичный собеседник. 
Напиши первое провокационное сообщение, которое вызовет у пользователя желание ответить.
Будь токсичным, саркастичным, но не переходи границы. Отвечай кратко: 1-3 предложения."""

        elif mode in ("mission", "scenario"):
            scenario_title = session_context.get(
                "scenario_title", "Токсичный собеседник"
            )
            scenario_desc = session_context.get("scenario_description", "")
            goals = session_context.get("goals", [])
            mission_desc = session_context.get("mission_description", "")

            goals_text = ""
            if goals:
                goal_names = {
                    "calm": "проверять спокойствие пользователя",
                    "boundaries": "проверять установление границ",
                    "facts": "уводить от фактов",
                    "deescalate": "провоцировать эскалацию",
                    "manipulation": "использовать манипуляции",
                }
                goals_text = "Твоя скрытая задача: " + ", ".join(
                    [goal_names.get(g, g) for g in goals]
                )

            prompt = f"""Ты играешь роль токсичного собеседника в сценарии: "{scenario_title}".

Контекст ситуации: {scenario_desc}
{mission_desc}

{goals_text}

Начни диалог с пользователем. Напиши первое провокационное сообщение, соответствующее сценарию.
Будь токсичным, но реалистичным. Отвечай кратко: 1-3 предложения.
НЕ выходи из роли, НЕ объясняй что ты делаешь."""

        else:
            prompt = """Начни диалог с пользователем. Ты токсичный собеседник. 
Напиши первое провокационное сообщение. Отвечай кратко: 1-3 предложения."""

        # Отправляем запрос модели
        response = chat.send_command(prompt)

        # Сохраняем в историю
        db.save_message(user_id, "toxic", "Начало сессии", response)

        # Создаём контекст с информацией о сессии
        context = {
            "mode": mode,
            "session_context": session_context,
            "history": [{"user": "Начало сессии", "toxic": response}],
        }
        db.save_toxic_context(user_id, context, session_active=True)

        # Логируем событие
        db.log_event(
            user_id,
            "toxic_session_start",
            {"mode": mode, "scenario": session_context.get("scenario")},
        )

        # Отправляем первое сообщение пользователю
        bridge.send_message_to_user(
            user_id, response, reply_markup=get_toxic_no_keyboard()
        )

    except (ValueError, KeyError) as e:
        logger.error(
            f"[Toxic] Error parsing command in start_toxic_session: {e}", exc_info=True
        )
    except Exception as e:
        logger.exception(f"[Toxic] Unexpected error in start_toxic_session: {e}")


@router.handler(command="START_TOXIC_DEMO")
def start_toxic_demo(cmd: str, chat: Conversation):
    """
    Обработчик для демо-сессии токсичного собеседника (онбординг)
    Формат команды: START_TOXIC_DEMO user_id
    """
    try:
        # Парсим команду
        parts = cmd.split(" ", 1)
        if len(parts) != 2:
            return

        _, user_id = parts
        user_id = int(user_id)

        # Упрощённый промпт для демо
        prompt = """Ты токсичный коллега. Начни короткий диалог с пользователем.
Сценарий: ты просишь коллегу помочь с твоей работой, хотя это не его обязанность.
Будь настойчивым, но не слишком агрессивным — это демо-версия.
Напиши первое сообщение. 1-2 предложения."""

        # Отправляем запрос модели
        response = chat.send_command(prompt)

        # Сохраняем в историю
        db.save_message(user_id, "toxic_demo", "Начало демо", response)

        # Создаём контекст
        context = {
            "mode": "demo",
            "is_demo": True,
            "history": [{"user": "Начало демо", "toxic": response}],
        }
        db.save_toxic_context(user_id, context, session_active=True)

        # Отправляем сообщение
        bridge.send_message_to_user(
            user_id, response, reply_markup=get_toxic_no_keyboard()
        )

    except (ValueError, KeyError) as e:
        logger.error(
            f"[Toxic] Error parsing command in start_toxic_demo: {e}", exc_info=True
        )
    except Exception as e:
        logger.exception(f"[Toxic] Unexpected error in start_toxic_demo: {e}")


@router.handler(command="TOXIC_MESSAGE")
def toxic_message(cmd: str, chat: Conversation):
    """
    Обработчик для сообщения токсичного собеседника
    Формат команды: TOXIC_MESSAGE user_id&&user_message
    """
    try:
        # Парсим команду
        parts = cmd.split("&&", 1)
        if len(parts) != 2:
            return

        cmd_with_id, user_message = parts
        _, user_id = cmd_with_id.split(" ", 1)
        user_id = int(user_id)

        # Получаем контекст сессии
        context = db.get_toxic_context(user_id)
        history = context.get("history", []) if context else []
        mode = context.get("mode", "free") if context else "free"
        session_context = context.get("session_context", {}) if context else {}

        # Формируем запрос с учётом режима и истории
        if mode in ("mission", "scenario") and session_context:
            scenario_title = session_context.get(
                "scenario_title", "Токсичный собеседник"
            )
            scenario_desc = session_context.get("scenario_description", "")
            goals = session_context.get("goals", [])

            goals_text = ""
            if goals:
                goal_names = {
                    "calm": "проверяй спокойствие пользователя",
                    "boundaries": "проверяй, устанавливает ли он границы",
                    "facts": "уводи от фактов, используй эмоции",
                    "deescalate": "провоцируй эскалацию",
                    "manipulation": "используй манипуляции",
                }
                goals_text = "Помни: " + ", ".join(
                    [goal_names.get(g, g) for g in goals]
                )

            role_reminder = f"""Ты играешь роль в сценарии "{scenario_title}".
Контекст: {scenario_desc}
{goals_text}
НЕ выходи из роли!

"""
        else:
            role_reminder = ""

        # Формируем историю
        if history:
            history_text = "\n".join(
                [
                    f"Пользователь: {h['user']}\nТоксичный собеседник: {h['toxic']}"
                    for h in history[-5:]  # Последние 5 сообщений
                ]
            )
            prompt = f"""{role_reminder}История диалога:
{history_text}

Пользователь написал: {user_message}

Ответь токсично и провокационно, оставаясь в роли. 1-3 предложения."""
        else:
            prompt = f"""{role_reminder}Пользователь написал: {user_message}

Ответь токсично и провокационно. 1-3 предложения."""

        # Отправляем запрос модели
        response = chat.send_command(prompt)

        # Сохраняем в историю
        db.save_message(user_id, "toxic", user_message, response)

        # Обновляем контекст (сохраняем mode и session_context)
        if not context:
            context = {}
        if "history" not in context:
            context["history"] = []
        context["history"].append({"user": user_message, "toxic": response})
        db.save_toxic_context(user_id, context, session_active=True)

        # Логируем событие
        db.log_event(
            user_id, "toxic_message", {"message": user_message[:100], "mode": mode}
        )

        # Получаем контекст для редактирования сообщения "печатает..."
        context = db.get_toxic_context(user_id) or {}
        loading_msg_id = context.get("loading_msg_id")
        loading_chat_id = context.get("loading_chat_id")

        # Редактируем сообщение "печатает..." на ответ
        if loading_msg_id and loading_chat_id:
            bridge.edit_message(
                loading_chat_id,
                loading_msg_id,
                response,
                reply_markup=get_toxic_no_keyboard(),
            )
            # Очищаем из контекста
            if "loading_msg_id" in context:
                del context["loading_msg_id"]
            if "loading_chat_id" in context:
                del context["loading_chat_id"]
            db.save_toxic_context(user_id, context, session_active=True)
        else:
            bridge.send_message_to_user(
                user_id, response, reply_markup=get_toxic_no_keyboard()
            )

    except (ValueError, KeyError) as e:
        logger.error(
            f"[Toxic] Error parsing command in toxic_message: {e}", exc_info=True
        )
    except Exception as e:
        logger.exception(f"[Toxic] Unexpected error in toxic_message: {e}")


@router.handler(command="END_TOXIC")
def end_toxic_session(cmd: str, chat: Conversation):
    """
    Обработчик для завершения сессии токсичного собеседника (базовый)
    Формат команды: END_TOXIC user_id
    """
    try:
        # Парсим команду
        parts = cmd.split(" ", 1)
        if len(parts) != 2:
            return

        _, user_id = parts
        user_id = int(user_id)

        # Вызываем общий обработчик
        _process_end_toxic(user_id, chat, {})

    except (ValueError, KeyError) as e:
        logger.error(
            f"[Toxic] Error parsing command in end_toxic_session: {e}", exc_info=True
        )
    except Exception as e:
        logger.exception(f"[Toxic] Unexpected error in end_toxic_session: {e}")


@router.handler(command="END_TOXIC_EXTENDED")
def end_toxic_session_extended(cmd: str, chat: Conversation):
    """
    Обработчик для завершения сессии с расширенным контекстом
    Формат команды: END_TOXIC_EXTENDED user_id&&analysis_context_json
    """
    import json

    try:
        # Парсим команду
        parts = cmd.split("&&", 1)
        cmd_with_id = parts[0]
        analysis_context_json = parts[1] if len(parts) > 1 else "{}"

        _, user_id = cmd_with_id.split(" ", 1)
        user_id = int(user_id)

        try:
            analysis_context = json.loads(analysis_context_json)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(
                f"[Toxic] Failed to parse analysis_context_json: {e}, using empty context"
            )
            analysis_context = {}

        _process_end_toxic(user_id, chat, analysis_context)

    except (ValueError, KeyError) as e:
        logger.error(
            f"[Toxic] Error parsing command in end_toxic_session_extended: {e}",
            exc_info=True,
        )
    except Exception as e:
        logger.exception(f"[Toxic] Unexpected error in end_toxic_session_extended: {e}")


def _process_end_toxic(user_id: int, chat: Conversation, analysis_context: dict):
    """Общая логика завершения сессии"""
    import re

    # Получаем контекст сессии
    context = db.get_toxic_context(user_id)
    if not context:
        return

    history = context.get("history", [])
    if not history:
        return

    mode = context.get("mode", "free")
    session_context = context.get("session_context", {})

    # Объединяем контексты
    if analysis_context:
        mode = analysis_context.get("mode", mode)
        session_context = {**session_context, **analysis_context}

    history_text = "\n".join(
        [
            f"Пользователь: {h['user']}\nТоксичный собеседник: {h['toxic']}"
            for h in history
        ]
    )

    # Формируем промпт с учётом режима и целей
    goals = session_context.get("goals", [])
    scenario = session_context.get("scenario")
    mission_id = session_context.get("mission_id")

    goals_evaluation = ""
    if goals:
        goal_descriptions = {
            "calm": "Сохранение спокойствия",
            "boundaries": "Установление границ",
            "facts": "Возвращение к фактам",
            "deescalate": "Деэскалация конфликта",
            "manipulation": "Распознавание манипуляций",
        }
        goals_list = ", ".join([goal_descriptions.get(g, g) for g in goals])
        goals_evaluation = f"\nДОПОЛНИТЕЛЬНО оцени по выбранным целям: {goals_list}"

    scenario_context = ""
    if scenario:
        scenario_context = (
            f"\nСценарий сессии: {session_context.get('scenario_title', scenario)}"
        )

    prompt = f"""Проанализируй поведение пользователя в этом диалоге с токсичным собеседником.
{scenario_context}

История диалога:
{history_text}

ВАЖНО: Ты должен оценить пользователя по 3 сферам от 1 до 10 и дать развёрнутую обратную связь.

Формат ответа (СТРОГО соблюдай):
SCORES:boundaries=X,manipulation=Y,negotiation=Z
END_SCORES

Где X, Y, Z — числа от 1 до 10:
- boundaries (Границы): насколько хорошо пользователь устанавливал и защищал границы
- manipulation (Манипуляции): насколько хорошо распознавал манипуляции и защищался от них  
- negotiation (Переговоры): насколько эффективно вёл переговоры и искал компромисс
{goals_evaluation}

После SCORES дай развёрнутый анализ:
1. Общая оценка поведения
2. Что получилось хорошо
3. Что можно улучшить
4. Конкретные рекомендации

Будь поддерживающим и конструктивным."""

    # Отправляем запрос модели для анализа
    analysis_response = chat.send_command(prompt)

    # Парсим оценки из ответа
    boundaries_score = 5
    manipulation_score = 5
    negotiation_score = 5

    scores_match = re.search(
        r"SCORES:boundaries=(\d+),manipulation=(\d+),negotiation=(\d+)",
        analysis_response,
    )
    if scores_match:
        boundaries_score = int(scores_match.group(1))
        manipulation_score = int(scores_match.group(2))
        negotiation_score = int(scores_match.group(3))

    # Убираем технические метки из ответа
    clean_response = re.sub(
        r"SCORES:.*?END_SCORES\s*", "", analysis_response, flags=re.DOTALL
    )
    clean_response = clean_response.strip()

    # Сохраняем результаты и начисляем баллы
    total_points = db.save_toxic_result(
        user_id, boundaries_score, manipulation_score, negotiation_score, clean_response
    )

    # Бонус за миссию
    mission_bonus = 0
    if mission_id:
        from core.database import PointsConfig

        mission_bonus = PointsConfig.TOXIC_MISSION_BONUS
        # Добавляем бонусные баллы
        from core.database import Database

        sync_db = Database()
        conn = sync_db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_points (user_id, points, source, description)
            VALUES (?, ?, ?, ?)
        """,
            (user_id, mission_bonus, "toxic_mission", f"Бонус за миссию {mission_id}"),
        )
        conn.commit()
        conn.close()
        total_points += mission_bonus

    # Завершаем сессию
    db.end_toxic_session(user_id)

    # Сохраняем анализ
    db.save_message(user_id, "toxic_analysis", "Сессия завершена", clean_response)

    # Логируем событие
    db.log_event(
        user_id,
        "toxic_session_end",
        {
            "messages_count": len(history),
            "mode": mode,
            "scenario": scenario,
            "goals": goals,
            "boundaries_score": boundaries_score,
            "manipulation_score": manipulation_score,
            "negotiation_score": negotiation_score,
            "total_points": total_points,
        },
    )

    # Получаем общие баллы пользователя
    user_total_points = db.get_total_points(user_id)

    # Формируем ответ
    mode_text = ""
    if mode == "mission":
        mode_text = f"\n🎯 <b>Миссия завершена!</b>\n"
    elif mode == "scenario" and scenario:
        scenario_title = session_context.get("scenario_title", "")
        mode_text = f"\n📋 Сценарий: <b>{scenario_title}</b>\n"

    bonus_text = ""
    if mission_bonus:
        bonus_text = f"\n🎁 Бонус за миссию: +{mission_bonus}"

    result_text = f"""📊 <b>Анализ твоего поведения</b>
{mode_text}
<b>Оценка по сферам:</b>
🛡️ Границы: <b>{boundaries_score}/10</b>
🎭 Манипуляции: <b>{manipulation_score}/10</b>
🤝 Переговоры: <b>{negotiation_score}/10</b>

<b>Заработано баллов: +{total_points}</b>{bonus_text}
💎 Всего баллов: <b>{user_total_points}</b>

<b>Подробный анализ:</b>
{clean_response}"""

    # Получаем контекст для редактирования сообщения "Анализирую..."
    context = db.get_toxic_context(user_id) or {}
    loading_msg_id = context.get("analysis_loading_msg_id")
    loading_chat_id = context.get("analysis_loading_chat_id")

    # Выбираем клавиатуру
    from bot.keyboards.toxic_extended import get_toxic_result_keyboard

    keyboard = get_toxic_result_keyboard(has_mission=bool(mission_id))

    # Редактируем сообщение
    if loading_msg_id and loading_chat_id:
        bridge.edit_message(
            loading_chat_id, loading_msg_id, result_text, reply_markup=keyboard
        )
        # Очищаем из контекста
        if "analysis_loading_msg_id" in context:
            del context["analysis_loading_msg_id"]
        if "analysis_loading_chat_id" in context:
            del context["analysis_loading_chat_id"]
        db.save_toxic_context(user_id, context, session_active=False)
    else:
        bridge.send_message_to_user(user_id, result_text, reply_markup=keyboard)
