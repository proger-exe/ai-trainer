"""
Обработчики для модели ANALYSIS
"""

from AtlantSDK import AbstactRouter, Conversation
from core.database import Database
from core.bridge import bridge
from bot.keyboards import (
    get_continue_keyboard,
    get_home_keyboard,
    get_analysis_no_keyboard,
)

# Создаём роутер для модели ANALYSIS
router = AbstactRouter("ANALYSIS")
db = Database()


@router.handler(command="ANALYZE")
def analyze_situation(cmd: str, chat: Conversation):
    """
    Обработчик для анализа ситуации
    Формат команды: ANALYZE user_id&&situation_text
    """
    try:
        # Парсим команду
        parts = cmd.split("&&", 1)
        if len(parts) != 2:
            return

        cmd_with_id, situation_text = parts
        _, user_id = cmd_with_id.split(" ", 1)
        user_id = int(user_id)

        # Получаем контекст пользователя
        context = db.get_analysis_context(user_id)
        goal = context.get("goal") if context else None

        # Формируем запрос к модели
        if goal:
            prompt = f"Цель общения: {goal}\n\nСитуация: {situation_text}"
        else:
            prompt = situation_text

        # Отправляем запрос модели
        response = chat.send_command(prompt)

        # Проверяем, что ответ получен
        if not response or not response.strip():
            print(f"Warning: Empty response from model for user {user_id}")
            response = "Извините, не удалось получить ответ. Попробуйте переформулировать вопрос."

        print(f"Response received for user {user_id}, length: {len(response)} chars")
        # Проверяем, не обрезан ли ответ (если заканчивается на незавершённом предложении)
        if response and len(response) > 100:
            # Проверяем последние 100 символов на незавершённость
            last_chars = response[-100:]
            if not any(
                last_chars.endswith(ending)
                for ending in [".", "!", "?", ":", "\n", '"', "'", "»", "»"]
            ):
                print(f"Warning: Response might be truncated for user {user_id}")
                print(f"Last 200 chars: {response[-200:]}")

        # Сохраняем в историю
        db.save_message(user_id, "analysis", situation_text, response)

        # Обновляем контекст
        context_data = context.get("context_data", {}) if context else {}
        if "history" not in context_data:
            context_data["history"] = []
        context_data["history"].append(
            {"situation": situation_text, "response": response}
        )
        db.save_analysis_context(user_id, context_data, goal)

        # Логируем событие
        db.log_event(user_id, "analysis_request", {"situation": situation_text[:100]})

        # Получаем контекст для редактирования сообщения "Анализирую ситуацию..."
        context = db.get_analysis_context(user_id) or {}
        context_data = context.get("context_data", {}) if context else {}
        loading_msg_id = context_data.get("loading_msg_id")
        loading_chat_id = context_data.get("loading_chat_id")

        # Редактируем сообщение "Анализирую ситуацию..." на ответ
        if loading_msg_id and loading_chat_id:
            bridge.edit_message(
                loading_chat_id,
                loading_msg_id,
                response,
                reply_markup=get_continue_keyboard(),
            )
            # Очищаем из контекста
            if "loading_msg_id" in context_data:
                del context_data["loading_msg_id"]
            if "loading_chat_id" in context_data:
                del context_data["loading_chat_id"]
            db.save_analysis_context(user_id, context_data, goal)
        else:
            # Если нет сообщения для редактирования, отправляем новое
            bridge.send_message_to_user(
                user_id, response, reply_markup=get_continue_keyboard()
            )

    except Exception as e:
        print(f"Error in analyze_situation: {e}")


@router.handler(command="CONTINUE")
def continue_analysis(cmd: str, chat: Conversation):
    """
    Обработчик для продолжения разбора
    Формат команды: CONTINUE user_id&&question_text
    """
    try:
        # Парсим команду
        parts = cmd.split("&&", 1)
        if len(parts) != 2:
            return

        cmd_with_id, question_text = parts
        _, user_id = cmd_with_id.split(" ", 1)
        user_id = int(user_id)

        # Получаем контекст
        context = db.get_analysis_context(user_id)
        if not context:
            return

        # Формируем запрос с учётом истории
        history = context.get("context_data", {}).get("history", [])
        history_parts = []
        for h in history[-3:]:  # Последние 3 записи
            if "situation" in h:
                # Первоначальная ситуация
                history_parts.append(
                    f"Ситуация: {h['situation']}\nОтвет: {h['response']}"
                )
            elif "question" in h:
                # Продолжение разбора
                history_parts.append(f"Вопрос: {h['question']}\nОтвет: {h['response']}")
        history_text = "\n\n".join(history_parts)

        prompt = f"Контекст предыдущего разбора:\n{history_text}\n\nНовый вопрос: {question_text}"

        # Отправляем запрос модели
        response = chat.send_command(prompt)

        # Проверяем, что ответ получен
        if not response or not response.strip():
            print(f"Warning: Empty response from model for user {user_id}")
            response = "Извините, не удалось получить ответ. Попробуйте переформулировать вопрос."

        print(f"Response received for user {user_id}, length: {len(response)} chars")
        # Проверяем, не обрезан ли ответ (если заканчивается на незавершённом предложении)
        if response and len(response) > 100:
            # Проверяем последние 100 символов на незавершённость
            last_chars = response[-100:]
            if not any(
                last_chars.endswith(ending)
                for ending in [".", "!", "?", ":", "\n", '"', "'", "»", "»"]
            ):
                print(f"Warning: Response might be truncated for user {user_id}")
                print(f"Last 200 chars: {response[-200:]}")

        # Сохраняем в историю
        db.save_message(user_id, "analysis_continue", question_text, response)

        # Обновляем контекст
        context_data = context.get("context_data", {})
        if "history" not in context_data:
            context_data["history"] = []
        context_data["history"].append(
            {"question": question_text, "response": response}
        )

        # Получаем loading_msg_id ДО сохранения контекста
        loading_msg_id = context_data.get("loading_msg_id")
        loading_chat_id = context_data.get("loading_chat_id")

        # Очищаем loading_msg_id из контекста перед сохранением
        if "loading_msg_id" in context_data:
            del context_data["loading_msg_id"]
        if "loading_chat_id" in context_data:
            del context_data["loading_chat_id"]

        # Сохраняем обновлённый контекст
        db.save_analysis_context(user_id, context_data, context.get("goal"))

        # Редактируем сообщение "Анализирую..." на ответ или отправляем новое
        if loading_msg_id and loading_chat_id:
            try:
                bridge.edit_message(
                    loading_chat_id,
                    loading_msg_id,
                    response,
                    reply_markup=get_continue_keyboard(),
                )
                print(f"Edited message {loading_msg_id} for user {user_id}")
            except Exception as edit_error:
                print(
                    f"Error editing message: {edit_error}, sending new message instead"
                )
                bridge.send_message_to_user(
                    user_id, response, reply_markup=get_continue_keyboard()
                )
        else:
            # Если нет сообщения для редактирования, отправляем новое
            print(f"No loading message found, sending new message to user {user_id}")
            bridge.send_message_to_user(
                user_id, response, reply_markup=get_continue_keyboard()
            )

    except Exception as e:
        print(f"Error in continue_analysis: {e}")
        import traceback

        traceback.print_exc()


@router.handler(command="ONBOARDING_RECOMMEND")
def onboarding_recommend(cmd: str, chat: Conversation):
    """
    AI-рекомендация по результатам онбординга
    Формат команды: ONBOARDING_RECOMMEND user_id&&answers_json
    """
    try:
        import json

        # Парсим команду
        parts = cmd.split("&&", 1)
        if len(parts) != 2:
            return

        cmd_with_id, answers_json = parts
        _, user_id = cmd_with_id.split(" ", 1)
        user_id = int(user_id)

        answers = json.loads(answers_json)

        # Формируем профиль пользователя из ответов
        # Поддерживаем как новый формат (с текстами), так и старый (только индексы)
        profile_parts = []

        # Старые ключи для обратной совместимости
        old_key_mapping = {
            "main_challenge": "Основная проблема",
            "conflict_reaction": "Реакция на конфликт",
            "experience_level": "Уровень опыта",
            "priority_area": "Приоритетная сфера",
            "time_commitment": "Готовность по времени",
        }

        # Описания для старых ответов (fallback)
        old_descriptions = {
            "main_challenge": [
                "Сложно отстаивать свои границы",
                "Чувствует, что им манипулируют",
                "Не получается договариваться",
                "Встречает агрессию и токсичность",
            ],
            "conflict_reaction": [
                "Избегает и молчит",
                "Идёт в атаку",
                "Уступает, чтобы не ссориться",
                "Пытается обсудить спокойно",
            ],
            "experience_level": [
                "Начинающий — часто теряется",
                "Средний — иногда справляется",
                "Продвинутый — обычно справляется",
                "Эксперт — хочет отточить навыки",
            ],
            "priority_area": [
                "Работа и карьера",
                "Личные отношения",
                "Семья и родственники",
                "Друзья и знакомые",
            ],
            "time_commitment": [
                "5 минут в день",
                "15-20 минут в день",
                "Когда будет время",
                "Хочу пройти всё быстро",
            ],
        }

        # Формируем профиль
        for key, value in answers.items():
            if isinstance(value, dict) and "text" in value:
                # Новый формат: есть текст ответа
                profile_parts.append(f"- {value.get('question', key)}: {value['text']}")
            elif isinstance(value, int):
                # Старый формат: только индекс
                if key in old_key_mapping:
                    label = old_key_mapping[key]
                    descriptions = old_descriptions.get(key, [])
                    if 0 <= value < len(descriptions):
                        profile_parts.append(f"- {label}: {descriptions[value]}")
                    else:
                        profile_parts.append(f"- {label}: Ответ #{value + 1}")
                else:
                    profile_parts.append(f"- {key}: Ответ #{value + 1}")

        user_profile = (
            "\n".join(profile_parts) if profile_parts else "Данные не получены"
        )

        # Блоки обучения
        blocks = """
        1. Границы — установление и защита личных границ
        2. Манипуляции и агрессия — распознавание манипуляций и работа с токсичностью
        3. Переговоры — эффективные переговоры и достижение компромисса
        """

        prompt = f"""Проанализируй профиль пользователя и рекомендуй, с какого блока обучения ему лучше начать.

ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:
{user_profile}

ДОСТУПНЫЕ БЛОКИ ОБУЧЕНИЯ:
{blocks}

ВАЖНО: Ответ должен быть в формате:
RECOMMENDATION:block_id=N
END_RECOMMENDATION

Где N — номер блока (1, 2 или 3).

После тега END_RECOMMENDATION напиши персонализированное обращение к пользователю (2-3 предложения):
- Почему именно этот блок ему подходит
- Какие навыки он получит
- Мотивирующее завершение

Будь дружелюбным и поддерживающим. Обращайся на "ты"."""

        # Отправляем запрос модели
        response = chat.send_command(prompt)

        # Парсим рекомендацию
        import re

        block_match = re.search(r"RECOMMENDATION:block_id=(\d+)", response)
        recommended_block_id = int(block_match.group(1)) if block_match else 1

        # Убираем технические теги
        clean_response = re.sub(
            r"RECOMMENDATION:.*?END_RECOMMENDATION\s*", "", response, flags=re.DOTALL
        )
        clean_response = clean_response.strip()

        # Названия блоков
        block_titles = {1: "Границы", 2: "Манипуляции и агрессия", 3: "Переговоры"}
        block_title = block_titles.get(recommended_block_id, "Границы")

        # Сохраняем рекомендацию
        db.log_event(
            user_id,
            "onboarding_recommendation",
            {
                "answers": answers,
                "recommended_block": recommended_block_id,
                "recommendation": clean_response[:500],
            },
        )

        # Формируем ответ
        from bot.keyboards.onboarding_extended import (
            get_onboarding_recommendation_keyboard,
            get_onboarding_progress_indicator,
        )
        from bot.models.onboarding import OnboardingPhase

        progress = get_onboarding_progress_indicator(OnboardingPhase.RECOMMENDATION)

        result_text = f"""{progress}

🎯 <b>Персональная рекомендация</b>

На основе твоих ответов я рекомендую начать с блока:

<b>📚 {block_title}</b>

{clean_response}"""

        # Отправляем результат
        bridge.send_message_to_user(
            user_id,
            result_text,
            reply_markup=get_onboarding_recommendation_keyboard(
                recommended_block_id, block_title
            ),
        )

    except Exception as e:
        print(f"Error in onboarding_recommend: {e}")
        import traceback

        traceback.print_exc()

        # Fallback — рекомендуем первый блок
        from bot.keyboards.onboarding_extended import (
            get_onboarding_recommendation_keyboard,
        )

        bridge.send_message_to_user(
            user_id,
            "🎯 Рекомендую начать с блока <b>Границы</b> — это база для всех остальных навыков!",
            reply_markup=get_onboarding_recommendation_keyboard(1, "Границы"),
        )
